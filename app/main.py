import time
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import create_tables, check_db_connection
from app.models.user import User  # noqa: F401 — register model for table creation
from app.models.task import Task  # noqa: F401
from app.models.comment import Comment  # noqa: F401
from app.routes.auth import router as auth_router
from app.routes.tasks import router as tasks_router
from app.routes.comments import router as comments_router
from app.routes.unstable import router as unstable_router
from app.services.rate_limiter import check_rate_limit
from app.services.metrics import record_request, get_metrics

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("controlled_test_api")

app = FastAPI(
    title="Controlled Test API",
    description=(
        "A benchmark API that simulates realistic enterprise behavior — "
        "including intentional inconsistencies, validation gaps, and "
        "unstable endpoints — for the AI Test Engine to probe."
    ),
    version="0.1.0",
)


# ── Startup ───────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    logger.info("Creating database tables …")
    create_tables()
    logger.info("Database ready.")


# ── Routers ───────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(tasks_router)
app.include_router(comments_router)
app.include_router(unstable_router)


# ── Observability middleware ──────────────────────────────────────────
@app.middleware("http")
async def request_logging(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s → %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
    record_request(request.method, request.url.path, response.status_code, elapsed_ms)
    return response


# ── Rate-limit middleware ─────────────────────────────────────────────
RATE_LIMIT_EXEMPT = {"/health", "/metrics", "/", "/docs", "/openapi.json", "/redoc"}


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in RATE_LIMIT_EXEMPT:
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    exceeded = check_rate_limit(client_ip)
    if exceeded:
        return JSONResponse(
            status_code=429,
            content={"detail": exceeded["detail"]},
            headers={"Retry-After": str(exceeded["retry_after"])},
        )
    return await call_next(request)


# ── Health endpoint ───────────────────────────────────────────────────
# OPENAPI: no response_model — returns an untyped dict.
# The response shape (status, version, database) is not documented.
@app.get("/health", tags=["observability"], summary="Health check")
def health_check():
    db_ok = check_db_connection()
    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "version": app.version,
        "database": "connected" if db_ok else "unreachable",
    }


# ── Metrics endpoint ─────────────────────────────────────────────────
# OPENAPI IMPERFECTION: the description mentions some fields but
# the actual response has many more (endpoints, status_codes).
# No response_model — consumers must guess the structure.
@app.get(
    "/metrics",
    tags=["observability"],
    summary="Runtime metrics",
    description="Returns request count, error count, and average latency.",
    # IMPERFECTION: description is incomplete — doesn't mention
    # uptime_seconds, status_codes breakdown, or per-endpoint data
)
def metrics_endpoint():
    return get_metrics()


# ── Root ──────────────────────────────────────────────────────────────
@app.get("/", tags=["root"])
def root():
    return {
        "service": "Controlled Test API",
        "docs": "/docs",
        "health": "/health",
    }


# ── Global exception handler ─────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
