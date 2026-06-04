import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database.db import create_tables, get_connection
from app.ingestion import ingest_batch
from app.metrics import get_store_metrics
from app.funnel import get_funnel
from app.health import get_health
from app.anomalies import get_anomalies
from app.heatmap import get_heatmap
from app.logger import logger, new_trace_id

INGEST_BATCH_LIMIT = 500


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="Store Intelligence API", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    trace_id = new_trace_id()
    request.state.trace_id = trace_id
    start = time.monotonic()
    response = await call_next(request)
    latency_ms = round((time.monotonic() - start) * 1000)
    store_id = request.path_params.get("store_id", "-")
    logger.info(
        "request",
        extra={
            "trace_id": trace_id,
            "store_id": store_id,
            "endpoint": request.url.path,
            "latency_ms": latency_ms,
            "status_code": response.status_code,
        },
    )
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", new_trace_id())
    logger.error(f"Unhandled error: {exc}", extra={"trace_id": trace_id})
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "trace_id": trace_id},
    )


def _db_check():
    try:
        conn = get_connection()
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={"error": "database_unavailable", "message": str(e)},
        )


@app.get("/health")
def health():
    _db_check()
    return get_health()


@app.post("/events/ingest")
def ingest(request: Request, events: list[dict]):
    _db_check()
    if len(events) > INGEST_BATCH_LIMIT:
        raise HTTPException(
            status_code=422,
            detail=f"Batch exceeds limit of {INGEST_BATCH_LIMIT} events.",
        )
    result = ingest_batch(events)
    logger.info(
        "ingest",
        extra={
            "trace_id": getattr(request.state, "trace_id", "-"),
            "event_count": result["accepted"],
            "endpoint": "/events/ingest",
        },
    )
    return result


@app.get("/stores/{store_id}/metrics")
def metrics(store_id: str):
    _db_check()
    return get_store_metrics(store_id)


@app.get("/stores/{store_id}/funnel")
def funnel(store_id: str):
    _db_check()
    return get_funnel(store_id)


@app.get("/stores/{store_id}/heatmap")
def heatmap(store_id: str):
    _db_check()
    return get_heatmap(store_id)


@app.get("/stores/{store_id}/anomalies")
def anomalies(store_id: str):
    _db_check()
    return get_anomalies(store_id)
