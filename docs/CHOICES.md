# CHOICES.md — Three Key Decisions

---

## Decision 1: Detection Model — YOLOv8n

### Options considered
| Model | Pros | Cons |
|---|---|---|
| YOLOv8n | Fast, well-documented, pretrained COCO, easy Python API | Smaller than YOLOv8m/l — lower recall on partial occlusion |
| YOLOv8m | Better accuracy, still real-time | 3× slower, heavier Docker image |
| RT-DETR | Transformer-based, strong on crowded scenes | Complex setup, no simple pip install |
| MediaPipe | Very fast, runs on CPU | No bounding box confidence score, harder to track |

### What AI suggested
Claude suggested YOLOv8m or RT-DETR for retail scenes "because crowded billing areas require stronger detection." It specifically flagged that YOLOv8n struggles with partial occlusion at 1080p when multiple people overlap.

### What I chose and why
YOLOv8n — for two reasons:

1. **The challenge runs on a laptop.** YOLOv8n processes 1080p at ~20fps on CPU vs ~7fps for YOLOv8m. The acceptance gate requires the pipeline to actually run, not timeout.

2. **The confidence field compensates.** The spec says "do not suppress low-confidence events." YOLOv8n at conf=0.25 will emit partial-occlusion detections with low confidence scores (0.3–0.5), which is exactly what the scoring rubric wants — graceful degradation, not silent failure. A higher-accuracy model that drops low-confidence detections internally would actually score worse on schema compliance.

**Where AI was right:** In a production deployment I would use YOLOv8m or fine-tune on retail footage. For this challenge, YOLOv8n + honest confidence scores is the better trade-off.

**On VLM use:** I considered using GPT-4V for zone classification (prompt: "Given this frame, which zone — Entry, Main Floor, Billing — is this person standing in?"). I tested it on 10 frames. It was accurate but added 1.5–3 seconds per frame latency and required an API key in the Docker container. I chose rule-based zone classification (bounding box centroid vs zone polygon) instead. The VLM approach would be worthwhile if zone boundaries were irregular or if zones needed to be inferred from unlabelled footage.

---

## Decision 2: Event Schema Design

### Options considered
**Option A**: Flat schema — all fields at top level including `queue_depth`, `session_seq`.

**Option B**: Nested `metadata` object for event-type-specific fields, core fields flat.

**Option C**: Separate tables for different event types (events, dwell_events, queue_events).

### What AI suggested
Claude suggested Option A (flat schema) for "query simplicity — fewer JOINs." It argued that nested JSON in SQLite requires json_extract() which adds query complexity.

### What I chose and why
**Option B** — nested metadata. Reasons:

1. **The spec requires it.** The sample schema in the challenge document has `metadata: {queue_depth, sku_zone, session_seq}`. I matched the spec.

2. **Schema evolution.** Adding new metadata fields (e.g., `basket_size_estimate`) doesn't require ALTER TABLE — it's a JSON field. The core query fields (`store_id`, `event_type`, `timestamp`, `visitor_id`, `zone_id`) are all flat columns with indexes. The `queue_depth` value is additionally stored as a flat column on the events table for direct SQL querying without json_extract().

3. **Option C was rejected** because it creates JOIN complexity in every analytics query and makes partial-success ingest much harder to implement cleanly.

**Where I disagreed with AI:** Flat schema would have made the DB queries marginally simpler but would have broken spec compliance. The spec is the contract; I followed it and stored `queue_depth` as both a flat column and in metadata to get the best of both.

---

## Decision 3: API Architecture — Synchronous FastAPI + SQLite (no message queue)

### Options considered
**Option A**: FastAPI → direct SQLite writes → real-time query (what I built).

**Option B**: Detection pipeline → Kafka/Redis stream → consumer writes to Postgres → FastAPI reads.

**Option C**: FastAPI with async SQLite (aiosqlite) + background task queue.

### What AI suggested
Claude suggested Option B (Kafka + Postgres) for "production-grade event streaming." It argued this decouples ingestion throughput from query performance and handles burst traffic from 40 stores simultaneously.

### What I chose and why
**Option A** — synchronous FastAPI + SQLite. Reasons:

1. **Acceptance gate constraint**: `docker compose up` with no manual steps. Kafka requires Zookeeper + Kafka broker + schema registry — a 5-service compose file. One wrong env var and the reviewer gets a broken demo.

2. **The load doesn't justify it.** 40 stores × 3 cameras × ~2 events/second = ~240 events/second. SQLite handles 10,000+ writes/second on an SSD. This is not a Kafka problem.

3. **Idempotency is simpler.** With Kafka, deduplication requires either exactly-once semantics configuration or a separate dedup store. With `INSERT OR IGNORE` on a PK, idempotency is a single SQLite guarantee.

**Where AI was right about the future:** At true production scale — 40 stores, 15fps processing, 100ms event latency SLA — Option B is correct. The migration path is: replace the `ingest_batch()` function with a Kafka producer, add a consumer service that writes to Postgres, keep all API query logic identical. The SQLite→Postgres schema migration is straightforward since I used standard SQL throughout with no SQLite-specific functions.

**The first thing that breaks at scale** (as the follow-up question format asks): the `/funnel` endpoint runs a correlated subquery (`NOT EXISTS`) that is O(n²) in events per store. At 40 stores × 8 hours of events it becomes slow. Fix: materialise session state in a `sessions` table updated on every ingest, so funnel is a simple GROUP BY.
