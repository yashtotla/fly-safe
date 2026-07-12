"""fly-safe API entrypoint.

Informational only. Every value this API serves carries its source and freshness;
it asserts no opinion and fails safe (stale/unavailable over wrong).
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app import assembly, scheduler, seed
from app.catalog import ROUTES, get_route
from app.config import settings
from app.db import async_session, init_db
from app.models import SourceHealthRow

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with async_session() as session:
        await seed.seed_if_empty(session)  # dev: fixtures -> cache, no external calls
    task = asyncio.create_task(scheduler.run_scheduler()) if settings.poll_enabled else None
    try:
        yield
    finally:
        if task:
            task.cancel()


app = FastAPI(title="fly-safe API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    """Operational status per source (internal view — freshness of the actual data
    is exposed per-value in /route, not here)."""
    async with async_session() as session:
        rows = (await session.execute(select(SourceHealthRow))).scalars().all()
    return {
        "status": "ok",
        "poll_enabled": settings.poll_enabled,
        "sources": [
            {
                "source": r.source,
                "last_attempt_at": r.last_attempt_at,
                "last_success_at": r.last_success_at,
                "consecutive_failures": r.consecutive_failures,
                "last_error": r.last_error,
            }
            for r in rows
        ],
    }


@app.get("/routes")
async def routes() -> list[dict]:
    """Supported routes for the picker (only routes we can serve honestly)."""
    return [
        {
            "id": r.id,
            "label": r.label,
            "origin": r.origin,
            "hub": r.hub,
            "destination": r.destination,
            "airline": r.airline,
            "airline_name": r.airline_name,
        }
        for r in ROUTES.values()
    ]


@app.get("/route/{route_id}")
async def route(route_id: str, date: str | None = Query(default=None)) -> assembly.RouteBundle:
    r = get_route(route_id)
    if r is None:
        raise HTTPException(status_code=404, detail="unknown route")
    async with async_session() as session:
        return await assembly.build_bundle(session, r, date)
