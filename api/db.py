"""
資料庫初始化與 schema 定義。
dev 用 SQLite；換 PostgreSQL 時只需改連線字串與 aiosqlite → asyncpg。
"""

from pathlib import Path
import os
import aiosqlite
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = Path(os.getenv("DB_PATH", "./data/sec_extraction.db"))

_CREATE_FILINGS = """
CREATE TABLE IF NOT EXISTS filings (
    accession_number TEXT PRIMARY KEY,
    result_json      TEXT NOT NULL,
    fetched_at       TEXT NOT NULL,
    processing_ms    INTEGER
)
"""

_CREATE_JOBS = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id           TEXT PRIMARY KEY,
    status           TEXT NOT NULL DEFAULT 'pending',
    input_json       TEXT NOT NULL,
    accession_number TEXT,
    result_json      TEXT,
    error_message    TEXT,
    created_at       TEXT NOT NULL,
    completed_at     TEXT
)
"""

_CREATE_INDEXES = [
    """
    CREATE INDEX IF NOT EXISTS idx_filings_fetched_at
    ON filings(fetched_at)
    """,
    
    """
    CREATE INDEX IF NOT EXISTS idx_jobs_status
    ON jobs(status)
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_jobs_created_at
    ON jobs(created_at)
    """,

    """
    CREATE INDEX IF NOT EXISTS idx_jobs_accession_number
    ON jobs(accession_number)
    """,
]


async def init_db(db_path: Path = DATABASE_URL) -> None:
    os.makedirs(db_path.parent, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute(_CREATE_FILINGS)
        await db.execute(_CREATE_JOBS)
        for index in _CREATE_INDEXES:
            await db.execute(index)
        await db.commit()
