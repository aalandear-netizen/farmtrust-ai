"""FarmTrust AI – FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, make_asgi_app

from app.config import get_settings
from app.database import init_db
from app.routers import (
    audit,
    auth,
    farmers,
    government,
    insurance,
    loans,
    market,
    notifications,
    trust_scores,
)

settings = get_settings()
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))
logger = structlog.get_logger()

REQUEST_COUNT = Counter(
    "farmtrust_request_count", "Total HTTP requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "farmtrust_request_latency_seconds", "HTTP request latency", ["method", "path"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Starting FarmTrust AI API")
    await init_db()
    yield
    logger.info("Shutting down FarmTrust AI API")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered agricultural trust scoring and financial inclusion platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log each HTTP request and track Prometheus metrics."""
    import time

    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    REQUEST_COUNT.labels(
        method=request.method, path=request.url.path, status=response.status_code
    ).inc()
    REQUEST_LATENCY.labels(method=request.method, path=request.url.path).observe(
        duration
    )

    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )
    return response


# ─── Exception Handlers ───────────────────────────────────────────────────────


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal error occurred. Please try again later."},
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

PREFIX = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=PREFIX)
app.include_router(farmers.router, prefix=PREFIX)
app.include_router(trust_scores.router, prefix=PREFIX)
app.include_router(loans.router, prefix=PREFIX)
app.include_router(insurance.router, prefix=PREFIX)
app.include_router(market.router, prefix=PREFIX)
app.include_router(government.router, prefix=PREFIX)
app.include_router(audit.router, prefix=PREFIX)
app.include_router(notifications.router, prefix=PREFIX)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/health", tags=["Health"])
async def health_check():
    """Application health check endpoint."""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/", tags=["Root"])
async def root():
    """API root – returns basic information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
