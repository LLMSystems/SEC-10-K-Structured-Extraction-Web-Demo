"""
API 專用的 request / response schema。
不修改 src/models.py，避免污染核心資料結構。
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel

from sec_10k_pipeline.models import FilingOutput


class JobCreateRequest(BaseModel):
    cik: Optional[str] = None
    accession_number: Optional[str] = None
    url: Optional[str] = None


class JobCreateResponse(BaseModel):
    job_id: str
    status: str
    cache_hit: bool = False


class JobStatusResponse(BaseModel):
    job_id: str
    status: str                          # pending | running | done | failed
    result: Optional[FilingOutput] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
