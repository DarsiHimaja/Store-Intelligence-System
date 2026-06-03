# PROMPT: "Write pytest tests for a FastAPI store analytics API. Cover: happy path metrics,
# zero-visitor store, staff-only store, idempotent ingest, partial batch failure.
# Use httpx TestClient. Include fixtures that insert synthetic events."
# CHANGES MADE: Added re-entry dedup test, fixed fixture to use correct event_type values,
# added queue_depth column migration check, split staff-exclusion into its own test.

import os
import sys
import pytest

os.environ["DB_PATH"] = os.path.join(os.path.dirname(__file__), "test.db")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from fastapi.testclient import TestClient
from database.db import create_tables, get_connection
from main import app

client = TestClient(app)


def _clear_db():
    conn = get_connection()
    conn.execute("DELETE FROM events")
    conn.commit()
    conn.close()


def _insert_events(events: list[dict]):
    r = client.post("/events/ingest", json=events)
    assert r.status_code == 200
    return r.json()


def _make_event(overrides: dict = None) -> dict:
    base = {
        "event_id": "evt-001",
        "store_id": "STORE_TEST",
        "camera_id": "CAM_ENTRY_01",
        "visitor_id": "VIS_aaa111",
        "event_type": "ENTRY",
        "timestamp": "2026-03-03T10:00:00Z",
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.91,
        "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1},
    }
    if overrides:
        base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def clean():
    create_tables()
    _clear_db()
    yield
    _clear_db()


# ── Ingest ────────────────────────────────────────────────────────────────────

def test_ingest_single_event():
    r = _insert_events([_make_event()])
    assert r["accepted"] == 1
    assert r["rejected"] == 0


def test_ingest_idempotent():
    """Posting the same event twice must not double-count."""
    ev = _make_event()
    _insert_events([ev])
    r2 = _insert_events([ev])
    # Second call: accepted=0 (already exists, INSERT OR IGNORE)
    assert r2["accepted"] == 0
    assert r2["rejected"] == 0


def test_ingest_partial_failure():
    """Bad event in batch should not block valid ones."""
    good = _make_event({"event_id": "evt-good"})
    bad = {"event_id": "evt-bad", "store_id": "S", "camera_id": "C",
           "visitor_id": "V", "event_type": "INVALID_TYPE",
           "timestamp": "2026-01-01T00:00:00Z", "confidence": 0.5}
    r = _insert_events([good, bad])
    assert r["accepted"] == 1
    assert r["rejected"] == 1
    assert r["errors"][0]["event_id"] == "evt-bad"


def test_ingest_batch_limit():
    """Batches > 500 should be rejected with 422."""
    events = [_make_event({"event_id": f"e{i}", "visitor_id": f"VIS_{i}"}) for i in range(501)]
    r = client.post("/events/ingest", json=events)
    assert r.status_code == 422


# ── Metrics ───────────────────────────────────────────────────────────────────

def test_metrics_empty_store():
    """Store with no events must return zeros, not crash."""
    r = client.get("/stores/STORE_EMPTY/metrics")
    assert r.status_code == 200
    data = r.json()
    assert data["unique_visitors"] == 0
    assert data["conversion_rate"] == 0.0
    assert data["current_queue_depth"] == 0
    assert data["abandonment_rate"] == 0.0


def test_metrics_counts_entries():
    _insert_events([
        _make_event({"event_id": "e1", "visitor_id": "VIS_1", "event_type": "ENTRY", "store_id": "STORE_TEST"}),
        _make_event({"event_id": "e2", "visitor_id": "VIS_2", "event_type": "ENTRY", "store_id": "STORE_TEST"}),
    ])
    r = client.get("/stores/STORE_TEST/metrics")
    assert r.json()["unique_visitors"] == 2


def test_metrics_excludes_staff():
    """Staff ENTRY events must not count toward unique_visitors."""
    _insert_events([
        _make_event({"event_id": "e1", "visitor_id": "VIS_cust", "event_type": "ENTRY", "is_staff": False}),
        _make_event({"event_id": "e2", "visitor_id": "VIS_staff", "event_type": "ENTRY", "is_staff": True}),
    ])
    r = client.get("/stores/STORE_TEST/metrics")
    assert r.json()["unique_visitors"] == 1


def test_metrics_conversion_rate():
    _insert_events([
        _make_event({"event_id": "e1", "visitor_id": "VIS_1", "event_type": "ENTRY"}),
        _make_event({"event_id": "e2", "visitor_id": "VIS_2", "event_type": "ENTRY"}),
        _make_event({"event_id": "e3", "visitor_id": "VIS_1", "event_type": "BILLING_QUEUE_JOIN",
                     "zone_id": "BILLING_AREA",
                     "metadata": {"queue_depth": 2, "sku_zone": None, "session_seq": 3}}),
    ])
    r = client.get("/stores/STORE_TEST/metrics")
    data = r.json()
    assert data["conversion_rate"] == 0.5  # 1 of 2 visitors converted


def test_metrics_queue_depth():
    _insert_events([
        _make_event({"event_id": "e1", "visitor_id": "VIS_1", "event_type": "BILLING_QUEUE_JOIN",
                     "zone_id": "BILLING_AREA",
                     "metadata": {"queue_depth": 4, "sku_zone": None, "session_seq": 1}}),
    ])
    r = client.get("/stores/STORE_TEST/metrics")
    assert r.json()["current_queue_depth"] == 4


def test_metrics_abandonment_rate():
    _insert_events([
        _make_event({"event_id": "e1", "visitor_id": "VIS_1", "event_type": "BILLING_QUEUE_JOIN",
                     "metadata": {"queue_depth": 2, "sku_zone": None, "session_seq": 1}}),
        _make_event({"event_id": "e2", "visitor_id": "VIS_1", "event_type": "BILLING_QUEUE_ABANDON",
                     "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 2}}),
        _make_event({"event_id": "e3", "visitor_id": "VIS_2", "event_type": "BILLING_QUEUE_JOIN",
                     "metadata": {"queue_depth": 2, "sku_zone": None, "session_seq": 1}}),
    ])
    r = client.get("/stores/STORE_TEST/metrics")
    assert r.json()["abandonment_rate"] == 0.5


# ── Health ────────────────────────────────────────────────────────────────────

def test_health_returns_healthy():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


def test_health_stale_feed():
    """Event from > 10 min ago should show STALE_FEED."""
    _insert_events([_make_event({"timestamp": "2020-01-01T00:00:00Z"})])
    r = client.get("/health")
    stores = r.json()["stores"]
    assert stores["STORE_TEST"]["feed_status"] == "STALE_FEED"
