"""fly-safe API entrypoint.

Informational only. Every value this API serves carries its source and freshness;
it asserts no opinion and fails safe (stale/unavailable over wrong).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The in-process poll scheduler will start/stop here in a later phase.
    yield


app = FastAPI(title="fly-safe API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    """Liveness check. Per-source freshness/status lands here in a later phase."""
    return {"status": "ok"}
