from app.database.db import get_connection
from datetime import datetime, timezone, timedelta

STALE_THRESHOLD_MINUTES = 10


def get_health() -> dict:
    conn = get_connection()

    stores = conn.execute(
        "SELECT DISTINCT store_id FROM events"
    ).fetchall()

    store_status = {}
    now = datetime.now(timezone.utc)

    for row in stores:
        sid = row["store_id"]
        last_row = conn.execute(
            """
            SELECT timestamp FROM events
            WHERE store_id=? ORDER BY timestamp DESC LIMIT 1
            """,
            (sid,),
        ).fetchone()

        last_ts = last_row["timestamp"] if last_row else None
        feed_status = "OK"

        if last_ts:
            try:
                last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                lag = (now - last_dt).total_seconds() / 60
                if lag > STALE_THRESHOLD_MINUTES:
                    feed_status = "STALE_FEED"
            except ValueError:
                feed_status = "UNKNOWN"

        store_status[sid] = {
            "last_event_timestamp": last_ts,
            "feed_status": feed_status,
        }

    total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()

    return {
        "status": "healthy",
        "total_events": total_events,
        "stores": store_status,
        "checked_at": now.isoformat(),
    }
