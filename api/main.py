"""
FastAPI app 入口。

啟動：uvicorn api.main:app --reload
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import init_db
from cache import CacheService
from worker import JobWorker
from routes import router, init_routes

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173"
).split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    cache = CacheService()
    queue: asyncio.Queue = asyncio.Queue()
    init_routes(queue, cache)

    worker = JobWorker(queue, cache)
    worker_task = asyncio.create_task(worker.run())
    logger.info("API ready")

    yield

    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    logger.info("API shutdown")


app = FastAPI(title="SEC 10-K Extraction API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
