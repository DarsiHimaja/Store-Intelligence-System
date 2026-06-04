from app.database.db import get_connection


def get_store_metrics(store_id: str) -> dict:
    conn = get_connection()

    # Unique customer visitors (exclude staff)
    unique_visitors = conn.execute(
        """
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND is_staff=0 AND event_type='ENTRY'
        """,
        (store_id,),
    ).fetchone()[0]

    # Visitors who reached billing zone (proxy for purchase intent)
    billing_visitors = conn.execute(
        """
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND is_staff=0
          AND event_type IN ('BILLING_QUEUE_JOIN','ZONE_ENTER')
          AND zone_id IN ('BILLING','BILLING_AREA','BILLING_COUNTER')
        """,
        (store_id,),
    ).fetchone()[0]

    # Conversion: visitors who had a BILLING_QUEUE_JOIN (correlated with POS)
    converted = conn.execute(
        """
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND is_staff=0 AND event_type='BILLING_QUEUE_JOIN'
        """,
        (store_id,),
    ).fetchone()[0]

    conversion_rate = round(converted / unique_visitors, 4) if unique_visitors else 0.0

    # Avg dwell per zone (ms → seconds)
    zone_rows = conn.execute(
        """
        SELECT zone_id,
               AVG(dwell_ms) as avg_dwell_ms,
               COUNT(DISTINCT visitor_id) as visits
        FROM events
        WHERE store_id=? AND is_staff=0
          AND event_type IN ('ZONE_DWELL','ZONE_ENTER')
          AND zone_id IS NOT NULL
        GROUP BY zone_id
        """,
        (store_id,),
    ).fetchall()

    avg_dwell_per_zone = {
        r["zone_id"]: {
            "avg_dwell_seconds": round((r["avg_dwell_ms"] or 0) / 1000, 1),
            "visits": r["visits"],
        }
        for r in zone_rows
    }

    # Current queue depth (latest BILLING_QUEUE_JOIN queue_depth value)
    queue_row = conn.execute(
        """
        SELECT queue_depth FROM events
        WHERE store_id=? AND event_type='BILLING_QUEUE_JOIN'
          AND queue_depth IS NOT NULL
        ORDER BY timestamp DESC LIMIT 1
        """,
        (store_id,),
    ).fetchone()
    current_queue_depth = queue_row["queue_depth"] if queue_row else 0

    # Abandonment rate
    abandoned = conn.execute(
        """
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND is_staff=0 AND event_type='BILLING_QUEUE_ABANDON'
        """,
        (store_id,),
    ).fetchone()[0]

    queue_joiners = conn.execute(
        """
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND is_staff=0 AND event_type='BILLING_QUEUE_JOIN'
        """,
        (store_id,),
    ).fetchone()[0]

    abandonment_rate = round(abandoned / queue_joiners, 4) if queue_joiners else 0.0

    conn.close()

    return {
        "store_id": store_id,
        "unique_visitors": unique_visitors,
        "conversion_rate": conversion_rate,
        "avg_dwell_per_zone": avg_dwell_per_zone,
        "current_queue_depth": current_queue_depth,
        "abandonment_rate": abandonment_rate,
        "billing_zone_visitors": billing_visitors,
    }
