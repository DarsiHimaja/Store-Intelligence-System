"""
run.py — end-to-end: detect → emit events → ingest into API.

Usage:
    python pipeline/run.py [--api http://localhost:8000]
"""
import os
import sys
import json
import argparse
import subprocess
import requests

BATCH_SIZE = 200


def post_events(events_file: str, api_url: str):
    with open(events_file) as f:
        events = [json.loads(line) for line in f if line.strip()]

    print(f"Posting {len(events)} events to {api_url}/events/ingest ...")
    accepted = rejected = 0

    for i in range(0, len(events), BATCH_SIZE):
        batch = events[i: i + BATCH_SIZE]
        try:
            r = requests.post(f"{api_url}/events/ingest", json=batch, timeout=30)
            r.raise_for_status()
            data = r.json()
            accepted += data.get("accepted", 0)
            rejected += data.get("rejected", 0)
        except Exception as e:
            print(f"  Batch {i//BATCH_SIZE} failed: {e}")

    print(f"Done. Accepted={accepted} Rejected={rejected}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos",  default="dataset/videos")
    parser.add_argument("--layout",  default="dataset/layouts/store_layout.json")
    parser.add_argument("--store",   default="STORE_001")
    parser.add_argument("--output",  default="data/events/events.jsonl")
    parser.add_argument("--model",   default="yolov8n.pt")
    parser.add_argument("--api",     default="http://localhost:8000")
    parser.add_argument("--no-ingest", action="store_true",
                        help="Skip posting to API (just generate events file)")
    args = parser.parse_args()

    # Run detection
    detect_script = os.path.join(os.path.dirname(__file__), "detect.py")
    cmd = [
        sys.executable, detect_script,
        "--videos", args.videos,
        "--layout", args.layout,
        "--store",  args.store,
        "--output", args.output,
        "--model",  args.model,
    ]
    print("Running detection pipeline...")
    subprocess.run(cmd, check=True)

    if not args.no_ingest:
        post_events(args.output, args.api)


if __name__ == "__main__":
    main()
