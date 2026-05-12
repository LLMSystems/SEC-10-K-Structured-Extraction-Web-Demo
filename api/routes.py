"""
路由定義：POST /jobs, GET /jobs/{job_id}, GET /filings/{accession_number},
         POST /xbrl-markdown
queue 和 cache 由 main.py 在 lifespan 啟動時注入。
"""

from __future__ import annotations
import asyncio
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from models.job import JobCreateRequest, JobCreateResponse, JobStatusResponse
from cache import CacheService
from sec_10k_pipeline.models import FilingInput, FilingOutput
from utils import parse_sec_url
from item8_markdown import get_item8_markdown

logger = logging.getLogger(__name__)
router = APIRouter()

_queue: Optional[asyncio.Queue] = None
_cache: Optional[CacheService] = None


def init_routes(queue: asyncio.Queue, cache: CacheService) -> None:
    global _queue, _cache
    _queue = queue
    _cache = cache


@router.post("/jobs", response_model=JobCreateResponse, status_code=202)
async def create_job(req: JobCreateRequest):
    try:
        # 如果有 req.cik、req.accession_number 就用它們；否則嘗試從 req.url 解析。後者適合直接給 URL 的場景（P1）。
        print(f"Received job request: {req}")
        if req.cik and req.accession_number:
            filing_input = FilingInput(
                cik=req.cik,
                accession_number=req.accession_number,
                url=req.url,
            )
        elif req.url:
            cik, accession = await parse_sec_url(req.url)
            filing_input = FilingInput(
                cik=cik,
                accession_number=accession,
                url=None,
            )
        else:
            raise HTTPException(status_code=422, detail="Either cik+accession_number or url must be provided")
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    job_id = str(uuid.uuid4())
    accession_number = filing_input.accession_number
    input_json = filing_input.model_dump_json()

    # cache hit：已有結果，直接建 done job，不進 queue
    if accession_number:
        cached = await _cache.get_filing(accession_number)
        if cached is not None:
            await _cache.create_job_done(
                job_id, input_json, accession_number, cached.model_dump_json()
            )
            return JobCreateResponse(job_id=job_id, status="done", cache_hit=True)

    await _cache.create_job(job_id, input_json, accession_number)
    await _queue.put({
        "job_id": job_id,
        "input_json": input_json,
        "accession_number": accession_number,
    })

    return JobCreateResponse(job_id=job_id, status="pending", cache_hit=False)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(job_id: str):
    job = await _cache.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    result: Optional[FilingOutput] = None
    if job["status"] == "done" and job.get("result_json"):
        result = FilingOutput.model_validate_json(job["result_json"])

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        result=result,
        error=job.get("error_message"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
    )


@router.get("/filings/{accession_number}", response_model=FilingOutput)
async def get_filing(accession_number: str):
    """直接查 cache，bypass job 系統。cache miss 時回 404，不觸發處理。"""
    result = await _cache.get_filing(accession_number)
    if result is None:
        raise HTTPException(status_code=404, detail="Filing not found in cache")
    return result


class XbrlMarkdownRequest(BaseModel):
    cik: str
    accession_number: str

@router.post("/xbrl-markdown", response_class=PlainTextResponse)
async def create_xbrl_markdown(req: XbrlMarkdownRequest):
    """
    同步擷取 SEC XBRL 資料並渲染為 Markdown。
    直接返回 text/plain，適合快速預覽或下載。
    """
    try:
        markdown = await asyncio.to_thread(
            get_item8_markdown,
            req.cik,
            req.accession_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("xbrl-markdown failed for %s / %s", req.cik, req.accession_number)
        raise HTTPException(status_code=500, detail=str(exc))
    return PlainTextResponse(content=markdown, media_type="text/markdown; charset=utf-8")
