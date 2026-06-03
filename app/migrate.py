import sqlite3, sys

db_path = "store.db"
conn = sqlite3.connect(db_path)
cols = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]

with open("migrate_out.txt", "w") as f:
    f.write(f"Columns before: {cols}\n")
    if "queue_depth" not in cols:
        conn.execute("ALTER TABLE events ADD COLUMN queue_depth INTEGER")
        conn.commit()
        cols2 = [r[1] for r in conn.execute("PRAGMA table_info(events)").fetchall()]
        f.write(f"MIGRATED. Columns after: {cols2}\n")
    else:
        f.write("queue_depth already present\n")

conn.close()
