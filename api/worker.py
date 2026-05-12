"""
JobWorker：從 asyncio.Queue 取 job，呼叫 AsyncPipeline，把結果寫回 DB。
P0：單一 worker；P2 再加 in-flight dedup。
"""

from __future__ import annotations
import asyncio
import logging
import time

from cache import CacheService
from sec_10k_pipeline.async_pipeline import AsyncPipeline
from sec_10k_pipeline.models import FilingInput

logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(self, queue: asyncio.Queue, cache: CacheService):
        self.queue = queue
        self.cache = cache
        self.pipeline = AsyncPipeline()

    async def run(self) -> None:
        logger.info("Worker started")
        while True:
            job = await self.queue.get()
            try:
                await self._process(job)
            except Exception:
                logger.exception(f"Unexpected error on job {job['job_id']}")
            finally:
                self.queue.task_done()

    async def _process(self, job: dict) -> None:
        job_id = job["job_id"]
        logger.info(f"Processing job {job_id}")
        await self.cache.update_job_running(job_id)

        try:
            filing_input = FilingInput.model_validate_json(job["input_json"])
            t0 = time.monotonic()
            result = await self.pipeline.run_async(filing_input)
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            acc = job.get("accession_number")
            if acc:
                await self.cache.save_filing(acc, result, elapsed_ms)

            await self.cache.update_job_done(job_id, result.model_dump_json())
            logger.info(f"Job {job_id} done in {elapsed_ms}ms")

        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            await self.cache.update_job_failed(job_id, str(e))
