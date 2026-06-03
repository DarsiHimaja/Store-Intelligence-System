import sqlite3
import os

# In Docker: DB_PATH=/app/data/store.db  |  Local dev: app/store.db
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "store.db"))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS events (
        event_id    TEXT PRIMARY KEY,
        store_id    TEXT NOT NULL,
        camera_id   TEXT,
        visitor_id  TEXT NOT NULL,
        event_type  TEXT NOT NULL,
        timestamp   TEXT NOT NULL,
        zone_id     TEXT,
        dwell_ms    INTEGER DEFAULT 0,
        is_staff    INTEGER DEFAULT 0,
        confidence  REAL DEFAULT 0.0,
        queue_depth INTEGER,
        ingested_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_store_ts   ON events(store_id, timestamp);
    CREATE INDEX IF NOT EXISTS idx_visitor    ON events(visitor_id);
    CREATE INDEX IF NOT EXISTS idx_event_type ON events(store_id, event_type);
    """)
    # Safe migration: add any columns missing from older DB files
    existing = {r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
    for col, sql in [
        ("queue_depth", "ALTER TABLE events ADD COLUMN queue_depth INTEGER"),
        ("ingested_at",  "ALTER TABLE events ADD COLUMN ingested_at TEXT"),
    ]:
        if col not in existing:
            conn.execute(sql)
    conn.commit()
    conn.close()
