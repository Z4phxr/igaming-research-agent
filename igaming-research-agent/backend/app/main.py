"""FastAPI app entrypoint with CORS and router registration.

TODO: Add structured logging middleware and health endpoint metadata.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import queries as queries_router
from app.api import reports as reports_router
from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize DB and scheduler on startup; stop scheduler on shutdown."""
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="iGaming Research Agent API", version="0.1.0", lifespan=lifespan)

# Required CORS for local React frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(queries_router.router, prefix="/api/queries", tags=["queries"])
app.include_router(reports_router.router, prefix="/api/reports", tags=["reports"])


@app.get("/api/health", tags=["system"])
def health() -> dict:
    """Simple health check endpoint.

    TODO: Include last_run and next_run timestamps from scheduler state.
    """
    return {"status": "ok"}
