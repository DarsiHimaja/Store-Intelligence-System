# DESIGN.md — Store Intelligence System

## Architecture Overview

The system is a four-stage pipeline: raw CCTV → detection events → API ingestion → queryable analytics.

```
CCTV clips (mp4)
      │
      ▼
pipeline/detect.py        YOLOv8n person detection, every 5th frame
      │                   Custom IoU + color-histogram tracker (tracker.py)
      │                   Emits 8 event types → events.jsonl (emit.py)
      │
      ▼
POST /events/ingest       FastAPI (app/main.py)
      │                   Pydantic validation, INSERT OR IGNORE dedup
      │                   SQLite (store.db) with 3 indexes
      ▼
GET /stores/{id}/metrics  Real-time aggregation queries — no cache layer
GET /stores/{id}/funnel   Session-scoped, staff excluded
GET /stores/{id}/heatmap  Normalised 0-100 per zone
GET /stores/{id}/anomalies  Rule-based: queue spike, dead zone, conversion drop
GET /health               Per-store feed status + STALE_FEED warning
      │
      ▼
dashboard/app.py          Streamlit live dashboard — polls API every N seconds
```

### Storage choice
SQLite. For a single-store prototype with < 1M events/day it is sufficient, zero-ops, and survives a `docker compose up` on any machine without provisioning a Postgres instance. At 40 live stores with real-time feeds I would switch to Postgres with TimescaleDB for time-series efficiency (documented in CHOICES.md).

### Detection pipeline design
- **Frame skip**: process every 5th frame (3fps effective). This trades recall for speed — at 15fps a person crossing the entry threshold takes ~10 frames, so we cannot miss an ENTRY. Validated empirically on the test clips.
- **Staff heuristic**: bounding box height > 60% of frame height. Staff stand close to cameras (behind counter) and are consistently taller in frame. This is a heuristic and has false positives on children; a fine-tuned classifier would be the production approach.
- **Tracker**: custom IoU + color histogram Re-ID. IoU alone fails when two people cross paths — the histogram adds appearance similarity to disambiguate. Re-entry window is 120s: any track lost for < 120s that matches appearance is flagged REENTRY rather than a new ENTRY.

### Event schema decisions
Described in detail in CHOICES.md. Key points:
- `confidence` is always emitted, even for low-confidence detections, as required — the API consumer decides the threshold.
- `metadata.session_seq` increments per-event within a visitor session, enabling sequence analysis.
- `queue_depth` stored on `BILLING_QUEUE_JOIN` events as a snapshot, not a separate table.

### API design
- **Idempotency**: `INSERT OR IGNORE` on `event_id` PK. Calling ingest twice with the same payload is safe; the second call returns `accepted=0`.
- **Partial success**: the ingest endpoint validates each event independently. One malformed event does not block the rest of the batch. Errors are returned per-event in `errors[]`.
- **Graceful degradation**: all endpoints check DB connectivity first. If SQLite is unavailable (e.g., volume not mounted), the response is HTTP 503 with a structured JSON body — no raw Python tracebacks are ever sent to the client.
- **Structured logging**: every request emits a JSON log line with `trace_id`, `store_id`, `endpoint`, `latency_ms`, `status_code`. The ingest endpoint additionally logs `event_count`.

---

## AI-Assisted Decisions

### 1. Tracker architecture — agreed with AI suggestion
I asked Claude to compare IoU-only tracking vs IoU + appearance Re-ID for a retail CCTV scenario. It recommended adding a lightweight appearance feature (color histogram) because IoU breaks when people stand still or cross paths — common in billing queues. I agreed and implemented it. The histogram approach is much lighter than running a full ReID network (OSNet) and adequate for this footage resolution. I verified this by running the tracker on CAM 1 and checking that crossing-path scenarios produced stable visitor_ids.

### 2. SQLite vs Postgres — overrode AI suggestion
Claude initially suggested Postgres because "production systems need a proper database." I pushed back: the acceptance gate requires `docker compose up` on a clean machine with no setup steps. Adding Postgres means adding a second service, volume, init scripts, and health-check ordering. SQLite gives us ACID guarantees, zero ops cost, and the `data/store.db` file is trivially portable. I documented the Postgres migration path in CHOICES.md for when it matters.

### 3. Conversion rate definition — refined AI suggestion
I asked for help defining "conversion" without a `customer_id` in POS data. The AI suggested pure time-window correlation (any visitor in billing zone within 5 minutes of a transaction = converted). I refined this: my pipeline emits `BILLING_QUEUE_JOIN` events with a timestamp, and the funnel endpoint counts visitors who joined the queue and did **not** subsequently emit `BILLING_QUEUE_ABANDON`. This is more precise than raw time-window correlation because it uses the actual event stream rather than inferring from POS timestamps.
