# PROMPT: "Write pytest tests for a conversion funnel endpoint. Test: 4 stages correct,
# re-entry doesn't double-count, zero-purchase store returns valid JSON not null,
# drop-off percentages calculated correctly."
# CHANGES MADE: Added explicit re-entry test using REENTRY event_type,
# corrected drop-off calculation assertions, added all-staff funnel edge case.

import os
import sys
import pytest

os.environ["DB_PATH"] = os.path.join(os.path.dirname(__file__), "test.db")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from fastapi.testclient import TestClient
from database.db import create_tables, get_connection
from main import app

client = TestClient(app)
STORE = "STORE_FUNNEL"


def _clear():
    conn = get_connection()
    conn.execute("DELETE FROM events")
    conn.commit()
    conn.close()


def _ev(event_id, visitor_id, event_type, zone_id=None, is_staff=False, queue_depth=None):
    return {
        "event_id": event_id,
        "store_id": STORE,
        "camera_id": "CAM_01",
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": "2026-03-03T10:00:00Z",
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


def test_funnel_empty_store():
    r = client.get(f"/stores/{STORE}/funnel")
    assert r.status_code == 200
    data = r.json()
    assert data["overall_conversion_pct"] == 0.0
    for stage in data["stages"]:
        assert stage["visitors"] == 0


def test_funnel_full_journey():
    """3 visitors enter, 2 visit zones, 1 joins billing, 1 purchases."""
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_A", "ENTRY"),
        _ev("e2", "VIS_B", "ENTRY"),
        _ev("e3", "VIS_C", "ENTRY"),
        _ev("e4", "VIS_A", "ZONE_ENTER", "SKINCARE"),
        _ev("e5", "VIS_B", "ZONE_ENTER", "MOISTURISER"),
        _ev("e6", "VIS_A", "BILLING_QUEUE_JOIN", "BILLING_AREA", queue_depth=2),
        # VIS_A completes purchase (no abandon after join)
    ])
    r = client.get(f"/stores/{STORE}/funnel")
    data = r.json()
    stages = {s["stage"]: s for s in data["stages"]}

    assert stages["entry"]["visitors"] == 3
    assert stages["zone_visit"]["visitors"] == 2
    assert stages["billing_queue"]["visitors"] == 1
    assert stages["purchase"]["visitors"] == 1
    assert data["overall_conversion_pct"] == round(1/3 * 100, 1)


def test_funnel_dropoff_pct():
    """Drop-off % from entry(4) to zone(2) should be 50.0."""
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_1", "ENTRY"),
        _ev("e2", "VIS_2", "ENTRY"),
        _ev("e3", "VIS_3", "ENTRY"),
        _ev("e4", "VIS_4", "ENTRY"),
        _ev("e5", "VIS_1", "ZONE_ENTER", "SKINCARE"),
        _ev("e6", "VIS_2", "ZONE_ENTER", "HAIRCARE"),
    ])
    r = client.get(f"/stores/{STORE}/funnel")
    stages = {s["stage"]: s for s in r.json()["stages"]}
    assert stages["zone_visit"]["dropoff_pct"] == 50.0


def test_funnel_reentry_not_double_counted():
    """A visitor who exits and re-enters must count as 1 unique visitor."""
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_A", "ENTRY"),
        _ev("e2", "VIS_A", "EXIT"),
        _ev("e3", "VIS_A", "REENTRY"),   # same person, new session
        _ev("e4", "VIS_A", "ZONE_ENTER", "SKINCARE"),
    ])
    r = client.get(f"/stores/{STORE}/funnel")
    stages = {s["stage"]: s for s in r.json()["stages"]}
    # Should count 1 unique visitor at entry, not 2
    assert stages["entry"]["visitors"] == 1


def test_funnel_all_staff():
    """Store with only staff events should return 0 across all stages."""
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_STAFF1", "ENTRY", is_staff=True),
        _ev("e2", "VIS_STAFF1", "ZONE_ENTER", "SKINCARE", is_staff=True),
        _ev("e3", "VIS_STAFF1", "BILLING_QUEUE_JOIN", "BILLING_AREA", is_staff=True),
    ])
    r = client.get(f"/stores/{STORE}/funnel")
    data = r.json()
    for stage in data["stages"]:
        assert stage["visitors"] == 0


def test_funnel_abandon_not_purchased():
    """Visitor who abandons billing queue should not count as purchased."""
    client.post("/events/ingest", json=[
        _ev("e1", "VIS_A", "ENTRY"),
        _ev("e2", "VIS_A", "BILLING_QUEUE_JOIN", "BILLING_AREA", queue_depth=3),
        _ev("e3", "VIS_A", "BILLING_QUEUE_ABANDON"),
    ])
    r = client.get(f"/stores/{STORE}/funnel")
    stages = {s["stage"]: s for s in r.json()["stages"]}
    assert stages["billing_queue"]["visitors"] == 1
    assert stages["purchase"]["visitors"] == 0
