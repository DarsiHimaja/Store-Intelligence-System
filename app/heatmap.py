from app.database.db import get_connection

LOW_SESSION_THRESHOLD = 20


def get_heatmap(store_id: str) -> dict:
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT zone_id,
               COUNT(DISTINCT visitor_id) AS unique_visitors,
               COUNT(*) AS total_events,
               AVG(dwell_ms) AS avg_dwell_ms
        FROM events
        WHERE store_id=? AND is_staff=0
          AND zone_id IS NOT NULL
          AND event_type IN ('ZONE_ENTER','ZONE_DWELL')
        GROUP BY zone_id
        """,
        (store_id,),
    ).fetchall()

    total_sessions = conn.execute(
        """
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND is_staff=0 AND event_type='ENTRY'
        """,
        (store_id,),
    ).fetchone()[0]

    conn.close()

    if not rows:
        return {"store_id": store_id, "zones": [], "data_confidence": "LOW"}

    max_visits = max(r["unique_visitors"] for r in rows) or 1
    max_dwell = max(r["avg_dwell_ms"] or 0 for r in rows) or 1

    zones = []
    for r in rows:
        visit_score = round(r["unique_visitors"] / max_visits * 100)
        dwell_score = round((r["avg_dwell_ms"] or 0) / max_dwell * 100)
        zones.append({
            "zone_id": r["zone_id"],
            "unique_visitors": r["unique_visitors"],
            "avg_dwell_seconds": round((r["avg_dwell_ms"] or 0) / 1000, 1),
            "visit_score": visit_score,
            "dwell_score": dwell_score,
        })

    zones.sort(key=lambda z: z["visit_score"], reverse=True)

    return {
        "store_id": store_id,
        "zones": zones,
        "data_confidence": "LOW" if total_sessions < LOW_SESSION_THRESHOLD else "OK",
    }
