import json
import requests

EVENTS_FILE = "data/events/events.jsonl"
API_URL = "http://localhost:8000"
BATCH_SIZE = 200

with open(EVENTS_FILE, "r") as f:
    events = [json.loads(line) for line in f if line.strip()]

print(f"Loaded {len(events)} events")

accepted = rejected = 0

for i in range(0, len(events), BATCH_SIZE):
    batch = events[i:i + BATCH_SIZE]
    r = requests.post(f"{API_URL}/events/ingest", json=batch)
    data = r.json()
    accepted += data.get("accepted", 0)
    rejected += data.get("rejected", 0)
    print(f"  Batch {i//BATCH_SIZE + 1}: status={r.status_code} accepted={data.get('accepted')} rejected={data.get('rejected')}")

print(f"\nDone. Total accepted={accepted} rejected={rejected}")
