from app.database.db import get_connection


def get_funnel(store_id: str) -> dict:
    conn = get_connection()

    # Stage 1: unique customer sessions that entered (ENTRY event, deduplicated by visitor_id)
    entries = conn.execute(
        """
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND is_staff=0 AND event_type='ENTRY'
        """,
        (store_id,),
    ).fetchone()[0]

    # Stage 2: of those, how many visited at least one named zone
    zone_visitors = conn.execute(
        """
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND is_staff=0
          AND event_type IN ('ZONE_ENTER','ZONE_DWELL')
          AND zone_id IS NOT NULL
          AND visitor_id IN (
              SELECT DISTINCT visitor_id FROM events
              WHERE store_id=? AND is_staff=0 AND event_type='ENTRY'
          )
        """,
        (store_id, store_id),
    ).fetchone()[0]

    # Stage 3: reached billing queue
    billing_queue = conn.execute(
        """
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND is_staff=0 AND event_type='BILLING_QUEUE_JOIN'
        """,
        (store_id,),
    ).fetchone()[0]

    # Stage 4: completed purchase — BILLING_QUEUE_JOIN with NO abandon after it,
    # but only counting visitors who actually joined the queue
    purchased = conn.execute(
        """
        SELECT COUNT(DISTINCT j.visitor_id)
        FROM events j
        WHERE j.store_id=? AND j.is_staff=0 AND j.event_type='BILLING_QUEUE_JOIN'
          AND NOT EXISTS (
              SELECT 1 FROM events a
              WHERE a.store_id=j.store_id
                AND a.visitor_id=j.visitor_id
                AND a.event_type='BILLING_QUEUE_ABANDON'
          )
        """,
        (store_id,),
    ).fetchone()[0]

    conn.close()

    def drop(a, b):
        return round((a - b) / a * 100, 1) if a else 0.0

    return {
        "store_id": store_id,
        "stages": [
            {"stage": "entry",         "visitors": entries,       "dropoff_pct": 0.0},
            {"stage": "zone_visit",    "visitors": zone_visitors, "dropoff_pct": drop(entries, zone_visitors)},
            {"stage": "billing_queue", "visitors": billing_queue, "dropoff_pct": drop(zone_visitors, billing_queue)},
            {"stage": "purchase",      "visitors": purchased,     "dropoff_pct": drop(billing_queue, purchased)},
        ],
        "overall_conversion_pct": round(purchased / entries * 100, 1) if entries else 0.0,
    }
