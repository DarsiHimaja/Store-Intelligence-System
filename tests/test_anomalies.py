# PROMPT: "Write pytest tests for anomaly detection and heatmap endpoints. Cover:
# queue spike triggers at correct threshold, dead zone after 30 min inactivity,
# conversion drop detected vs baseline, heatmap data_confidence flag on low sessions."
# CHANGES MADE: Used datetime manipulation to simulate time windows accurately,
# corrected severity threshold (CRITICAL = 2x spike threshold = 10), added
# heatmap normalisation assertion.

import os
import sys
import pytest
from datetime import datetime, timezone, timedelta

os.environ["DB_PATH"] = os.path.join(os.path.dirname(__file__), "test.db")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from fastapi.testclient import TestClient
from database.db import create_tables, get_connection
from main import app

client = TestClient(app)
STORE = "STORE_ANOM"


def _clear():
    conn = get_connection()
    conn.execute("DELETE FROM events")
    conn.commit()
    conn.close()


def _ev(event_id, visitor_id, event_type, zone_id=None, queue_depth=None,
        ts=None, is_staff=False):
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()
    return {
        "event_id": event_id,
        "store_id": STORE,
        "camera_id": "CAM_01",
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": ts,
        "zone_id": zone_id,
        "dwell_ms": 0,
        "is_staff": is_staff,
        "confidence": 0.85,
        "metadata": {"queue_depth": queue_depth, "sku_zone": zone_id, "session_seq": 1},
    }


@pytest.fixture(autouse=True)
def clean():
    create_tables()
    _clear()
    yield
    _clear()


# ── Anomalies ─────────────────────────────────────────────────────────────────

def test_no_anomalies_empty_store():
    r = client.get(f"/stores/{STORE}/anomalies")
    assert r.status_code == 200
    assert r.json()["anomalies"] == []


def test_queue_spike_warn():
    """Queue depth >= 5 should trigger WARN."""
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_1", "BILLING_QUEUE_JOIN", "BILLING_AREA", queue_depth=5),
    ])
    r = client.get(f"/stores/{STORE}/anomalies")
    types = [a["type"] for a in r.json()["anomalies"]]
    severities = {a["type"]: a["severity"] for a in r.json()["anomalies"]}
    assert "BILLING_QUEUE_SPIKE" in types
    assert severities["BILLING_QUEUE_SPIKE"] == "WARN"


def test_queue_spike_critical():
    """Queue depth >= 10 should trigger CRITICAL."""
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_1", "BILLING_QUEUE_JOIN", "BILLING_AREA", queue_depth=10),
    ])
    r = client.get(f"/stores/{STORE}/anomalies")
    severities = {a["type"]: a["severity"] for a in r.json()["anomalies"]}
    assert severities.get("BILLING_QUEUE_SPIKE") == "CRITICAL"


def test_queue_below_threshold_no_spike():
    """Queue depth of 3 should NOT trigger spike."""
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_1", "BILLING_QUEUE_JOIN", "BILLING_AREA", queue_depth=3),
    ])
    r = client.get(f"/stores/{STORE}/anomalies")
    types = [a["type"] for a in r.json()["anomalies"]]
    assert "BILLING_QUEUE_SPIKE" not in types


def test_dead_zone_detected():
    """Zone with no visits in last 30 min should show DEAD_ZONE."""
    old_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_1", "ZONE_ENTER", "SKINCARE", ts=old_ts),
    ])
    r = client.get(f"/stores/{STORE}/anomalies")
    types = [a["type"] for a in r.json()["anomalies"]]
    assert "DEAD_ZONE" in types


def test_active_zone_no_dead_zone():
    """Zone with recent visit should NOT trigger dead zone."""
    recent_ts = datetime.now(timezone.utc).isoformat()
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_1", "ZONE_ENTER", "SKINCARE", ts=recent_ts),
    ])
    r = client.get(f"/stores/{STORE}/anomalies")
    dead = [a for a in r.json()["anomalies"] if a["type"] == "DEAD_ZONE"]
    assert len(dead) == 0


def test_anomaly_has_suggested_action():
    """Every anomaly must include a suggested_action string."""
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_1", "BILLING_QUEUE_JOIN", "BILLING_AREA", queue_depth=5),
    ])
    r = client.get(f"/stores/{STORE}/anomalies")
    for anomaly in r.json()["anomalies"]:
        assert "suggested_action" in anomaly
        assert len(anomaly["suggested_action"]) > 0


# ── Heatmap ───────────────────────────────────────────────────────────────────

def test_heatmap_empty():
    r = client.get(f"/stores/{STORE}/heatmap")
    assert r.status_code == 200
    data = r.json()
    assert data["zones"] == []
    assert data["data_confidence"] == "LOW"


def test_heatmap_low_confidence_flag():
    """Fewer than 20 sessions → data_confidence = LOW."""
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_1", "ZONE_ENTER", "SKINCARE"),
        _ev("e2", "VIS_2", "ZONE_ENTER", "HAIRCARE"),
    ])
    r = client.get(f"/stores/{STORE}/heatmap")
    assert r.json()["data_confidence"] == "LOW"


def test_heatmap_scores_normalised():
    """Top zone by visitors should have visit_score=100."""
    events = []
    for i in range(5):
        events.append(_ev(f"e{i}", f"VIS_{i}", "ZONE_ENTER", "SKINCARE"))
    events.append(_ev("e99", "VIS_X", "ZONE_ENTER", "HAIRCARE"))
    client.post("/events/ingest", json=events)

    r = client.get(f"/stores/{STORE}/heatmap")
    zones = r.json()["zones"]
    scores = {z["zone_id"]: z["visit_score"] for z in zones}
    assert scores["SKINCARE"] == 100
    assert scores["HAIRCARE"] < 100
