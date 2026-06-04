from app.database.db import get_connection
from datetime import datetime, timezone, timedelta

QUEUE_SPIKE_THRESHOLD = 5
DEAD_ZONE_MINUTES = 30
CONVERSION_DROP_THRESHOLD = 0.3  # 30% below baseline triggers WARN


def get_anomalies(store_id: str) -> dict:
    conn = get_connection()
    anomalies = []
    now = datetime.now(timezone.utc)

    # --- Queue spike ---
    queue_row = conn.execute(
        """
        SELECT queue_depth FROM events
        WHERE store_id=? AND event_type='BILLING_QUEUE_JOIN'
          AND queue_depth IS NOT NULL
        ORDER BY timestamp DESC LIMIT 1
        """,
        (store_id,),
    ).fetchone()

    if queue_row and queue_row["queue_depth"] >= QUEUE_SPIKE_THRESHOLD:
        depth = queue_row["queue_depth"]
        severity = "CRITICAL" if depth >= QUEUE_SPIKE_THRESHOLD * 2 else "WARN"
        anomalies.append({
            "type": "BILLING_QUEUE_SPIKE",
            "severity": severity,
            "detail": f"Queue depth is {depth}",
            "suggested_action": "Deploy additional billing staff immediately.",
        })

    # --- Dead zones (no visits in last 30 min) ---
    cutoff = (now - timedelta(minutes=DEAD_ZONE_MINUTES)).isoformat()
    all_zones = conn.execute(
        """
        SELECT DISTINCT zone_id FROM events
        WHERE store_id=? AND zone_id IS NOT NULL AND is_staff=0
        """,
        (store_id,),
    ).fetchall()

    recent_zones = conn.execute(
        """
        SELECT DISTINCT zone_id FROM events
        WHERE store_id=? AND zone_id IS NOT NULL AND is_staff=0
          AND timestamp >= ?
        """,
        (store_id, cutoff),
    ).fetchall()

    recent_zone_ids = {r["zone_id"] for r in recent_zones}
    for row in all_zones:
        z = row["zone_id"]
        if z not in recent_zone_ids:
            anomalies.append({
                "type": "DEAD_ZONE",
                "severity": "INFO",
                "detail": f"Zone '{z}' has had no visits in the last {DEAD_ZONE_MINUTES} minutes.",
                "suggested_action": f"Check display or signage in zone {z}.",
            })

    # --- Conversion drop vs recent baseline ---
    # Compare last-hour conversion to prior 6-hour window
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    seven_hours_ago = (now - timedelta(hours=7)).isoformat()

    def conversion_in_window(start, end):
        entries = conn.execute(
            """
            SELECT COUNT(DISTINCT visitor_id) FROM events
            WHERE store_id=? AND is_staff=0 AND event_type='ENTRY'
              AND timestamp BETWEEN ? AND ?
            """,
            (store_id, start, end),
        ).fetchone()[0]
        purchases = conn.execute(
            """
            SELECT COUNT(DISTINCT visitor_id) FROM events
            WHERE store_id=? AND is_staff=0 AND event_type='BILLING_QUEUE_JOIN'
              AND timestamp BETWEEN ? AND ?
            """,
            (store_id, start, end),
        ).fetchone()[0]
        return purchases / entries if entries else None

    recent_conv = conversion_in_window(one_hour_ago, now.isoformat())
    baseline_conv = conversion_in_window(seven_hours_ago, one_hour_ago)

    if recent_conv is not None and baseline_conv and baseline_conv > 0:
        drop = (baseline_conv - recent_conv) / baseline_conv
        if drop >= CONVERSION_DROP_THRESHOLD:
            anomalies.append({
                "type": "CONVERSION_DROP",
                "severity": "WARN",
                "detail": f"Conversion dropped {round(drop*100)}% vs prior 6h baseline ({round(baseline_conv*100,1)}% → {round(recent_conv*100,1)}%).",
                "suggested_action": "Review floor staff coverage and check for queue abandonment spike.",
            })

    conn.close()

    return {"store_id": store_id, "anomalies": anomalies}
