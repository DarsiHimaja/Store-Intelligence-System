from app.database.db import get_connection
from app.models import Event
from pydantic import ValidationError


def insert_event(conn, event: Event):
    queue_depth = event.metadata.queue_depth if event.metadata else None
    conn.execute(
        """
        INSERT OR IGNORE INTO events
        (event_id, store_id, camera_id, visitor_id, event_type,
         timestamp, zone_id, dwell_ms, is_staff, confidence, queue_depth)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            event.event_id, event.store_id, event.camera_id,
            event.visitor_id, event.event_type, event.timestamp,
            event.zone_id, event.dwell_ms, int(event.is_staff),
            event.confidence, queue_depth,
        ),
    )


def ingest_batch(raw_events: list[dict]) -> dict:
    accepted, rejected = [], []

    valid_events = []
    for raw in raw_events:
        try:
            valid_events.append(Event(**raw))
        except (ValidationError, Exception) as e:
            rejected.append({"event_id": raw.get("event_id"), "error": str(e)})

    if valid_events:
        conn = get_connection()
        try:
            for ev in valid_events:
                # Check if already exists (idempotency)
                exists = conn.execute(
                    "SELECT 1 FROM events WHERE event_id=?", (ev.event_id,)
                ).fetchone()
                if not exists:
                    insert_event(conn, ev)
                    accepted.append(ev.event_id)
            conn.commit()
        finally:
            conn.close()

    return {
        "accepted": len(accepted),
        "rejected": len(rejected),
        "errors": rejected,
    }
