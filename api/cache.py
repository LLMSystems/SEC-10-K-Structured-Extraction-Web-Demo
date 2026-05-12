"""
CacheService：封裝所有 DB 讀寫操作。
jobs table 追蹤請求狀態；filings table 存解析結果 cache。
"""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from db import DATABASE_URL
from sec_10k_pipeline.models import FilingOutput


class CacheService:
    def __init__(self, db_path: Path = DATABASE_URL):
        self.db_path = db_path

    # ── filings ──────────────────────────────────────────────

    async def get_filing(self, accession_number: str) -> Optional[FilingOutput]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT result_json FROM filings WHERE accession_number = ?",
                (accession_number,),
            ) as cursor:
                row = await cursor.fetchone()
                return FilingOutput.model_validate_json(row[0]) if row else None

    async def save_filing(
        self,
        accession_number: str,
        result: FilingOutput,
        processing_ms: int,
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO filings
                    (accession_number, result_json, fetched_at, processing_ms)
                VALUES (?, ?, ?, ?)
                """,
                (
                    accession_number,
                    result.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                    processing_ms,
                ),
            )
            await db.commit()

    # ── jobs ─────────────────────────────────────────────────

    async def create_job(
        self,
        job_id: str,
        input_json: str,
        accession_number: Optional[str],
    ) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO jobs (job_id, status, input_json, accession_number, created_at)
                VALUES (?, 'pending', ?, ?, ?)
                """,
                (job_id, input_json, accession_number, _now()),
            )
            await db.commit()

    async def get_job(self, job_id: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def update_job_running(self, job_id: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE jobs SET status = 'running' WHERE job_id = ?", (job_id,)
            )
            await db.commit()

    async def update_job_done(self, job_id: str, result_json: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE jobs
                SET status = 'done', result_json = ?, completed_at = ?
                WHERE job_id = ?
                """,
                (result_json, _now(), job_id),
            )
            await db.commit()

    async def create_job_done(
        self,
        job_id: str,
        input_json: str,
        accession_number: str,
        result_json: str,
    ) -> None:
        """cache hit 專用：直接以 done 狀態建立 job，跳過 queue。"""
        now = _now()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO jobs
                    (job_id, status, input_json, accession_number, result_json, created_at, completed_at)
                VALUES (?, 'done', ?, ?, ?, ?, ?)
                """,
                (job_id, input_json, accession_number, result_json, now, now),
            )
            await db.commit()

    async def update_job_failed(self, job_id: str, error: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE jobs
                SET status = 'failed', error_message = ?, completed_at = ?
                WHERE job_id = ?
                """,
                (error, _now(), job_id),
            )
            await db.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
