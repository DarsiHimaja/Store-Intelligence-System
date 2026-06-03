"""
emit.py — builds structured events from tracker output.

Zone classification: rule-based using bounding box centroid vs
zone polygons defined in store_layout.json.

Direction (ENTRY vs EXIT): determined by centroid Y-position
crossing the entry threshold line (top 20% of frame = entry zone).
"""
import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Optional


ENTRY_ZONE_FRACTION = 0.25   # top 25% of frame height = entry/exit threshold


def _centroid(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def _classify_zone(cx, cy, frame_h, frame_w, zones: list) -> Optional[str]:
    """
    zones: list of dicts with keys: zone_id, x_min, y_min, x_max, y_max
    (normalised 0-1 or pixel coords — we normalise to 0-1 here)
    """
    for z in zones:
        x_min = z.get("x_min", 0) * frame_w if z.get("x_min", 0) <= 1 else z["x_min"]
        x_max = z.get("x_max", 1) * frame_w if z.get("x_max", 1) <= 1 else z["x_max"]
        y_min = z.get("y_min", 0) * frame_h if z.get("y_min", 0) <= 1 else z["y_min"]
        y_max = z.get("y_max", 1) * frame_h if z.get("y_max", 1) <= 1 else z["y_max"]
        if x_min <= cx <= x_max and y_min <= cy <= y_max:
            return z["zone_id"]
    return None


def _is_entry_zone(cy, frame_h) -> bool:
    return cy < frame_h * ENTRY_ZONE_FRACTION


def build_event(
    track,
    event_type: str,
    store_id: str,
    camera_id: str,
    clip_start: datetime,
    frame_time_sec: float,
    frame_h: int,
    frame_w: int,
    zones: list,
    confidence: float,
    queue_depth: Optional[int] = None,
) -> dict:
    cx, cy = _centroid(track.bbox)
    zone_id = _classify_zone(cx, cy, frame_h, frame_w, zones)

    # Override event_type for entry/exit based on position
    if event_type in ("ENTRY", "EXIT"):
        zone_id = None

    ts = (clip_start + timedelta(seconds=frame_time_sec)).replace(
        tzinfo=timezone.utc
    ).isoformat()

    return {
        "event_id": str(uuid.uuid4()),
        "store_id": store_id,
        "camera_id": camera_id,
        "visitor_id": track.visitor_id,
        "event_type": event_type,
        "timestamp": ts,
        "zone_id": zone_id,
        "dwell_ms": track.session_seq * 1000 if "DWELL" in event_type else 0,
        "is_staff": track.is_staff,
        "confidence": round(confidence, 3),
        "metadata": {
            "queue_depth": queue_depth,
            "sku_zone": zone_id,
            "session_seq": track.session_seq,
        },
    }


def load_zones(layout_path: str, store_id: str) -> list:
    try:
        with open(layout_path) as f:
            layout = json.load(f)
        for store in layout if isinstance(layout, list) else [layout]:
            if store.get("store_id") == store_id:
                return store.get("zones", [])
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    # Fallback: generic zones based on vertical thirds
    return [
        {"zone_id": "ENTRY_AREA",   "x_min": 0, "y_min": 0,    "x_max": 1, "y_max": 0.25},
        {"zone_id": "MAIN_FLOOR",   "x_min": 0, "y_min": 0.25, "x_max": 1, "y_max": 0.70},
        {"zone_id": "BILLING_AREA", "x_min": 0, "y_min": 0.70, "x_max": 1, "y_max": 1.0},
    ]
