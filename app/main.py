"""Smart Bhopal - Grievance Redressal System API.

Run locally:
    uvicorn app.main:app --reload
Interactive docs: http://localhost:8000/docs
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import (
    admin,
    auth,
    authority,
    certificates,
    complaints,
    meta,
    ngo,
    nodal,
    notifications,
    rewards,
    uploads,
    worker,
)

logger = logging.getLogger("smart_bhopal")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if os.getenv("SEED_ON_STARTUP", "1").lower() in ("1", "true", "yes"):
        try:
            from app.seed import ensure_seed

            ensure_seed()
        except Exception as exc:  # pragma: no cover - seeding is best-effort
            logger.warning("Seed skipped: %s", exc)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Citizen-centric grievance redressal backend with verified "
                "resolution, escalation, gamification and analytics.",
    lifespan=lifespan,
)

# --- Middleware (safety + performance) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=512)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Serve uploaded media at /media (upload action lives at POST /uploads).
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.UPLOAD_DIR), name="media")

# --- Routers ---
app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(worker.router)
app.include_router(ngo.router)
app.include_router(nodal.router)
app.include_router(authority.router)
app.include_router(admin.router)
app.include_router(rewards.router)
app.include_router(notifications.router)
app.include_router(certificates.router)
app.include_router(meta.router)
app.include_router(uploads.router)


@app.get("/", tags=["Health"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
