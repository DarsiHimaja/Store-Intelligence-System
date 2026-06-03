"""
detect.py — processes CCTV clips with YOLOv8 + custom tracker.

Usage:
    python pipeline/detect.py --videos dataset/videos \
                               --layout dataset/layouts/store_layout.json \
                               --store STORE_001 \
                               --output data/events/events.jsonl

Staff detection: persons whose bounding box height > STAFF_HEIGHT_FRACTION
of frame height AND appear in >STAFF_FRAME_RATIO of frames are flagged staff.
This is a heuristic; a fine-tuned classifier would be more accurate.
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone

import cv2
from ultralytics import YOLO

# Allow running from repo root
sys.path.insert(0, os.path.dirname(__file__))
from tracker import Tracker
from emit import build_event, load_zones, _is_entry_zone, _centroid

FRAME_SKIP = 5              # process every Nth frame (balance speed vs accuracy)
CONF_THRESHOLD = 0.25       # minimum YOLO confidence to emit event
STAFF_HEIGHT_FRACTION = 0.6 # bbox height > 60% of frame → candidate staff
DWELL_EMIT_INTERVAL = 30    # emit ZONE_DWELL every 30 seconds of continuous dwell
BILLING_ZONES = {"BILLING", "BILLING_AREA", "BILLING_COUNTER"}


def detect_video(video_path, store_id, camera_id, layout_path, output_file, model):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 15
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    # Clip start time: use file mtime as proxy, or epoch
    try:
        mtime = os.path.getmtime(video_path)
        clip_start = datetime.fromtimestamp(mtime, tz=timezone.utc)
    except Exception:
        clip_start = datetime(2026, 3, 3, 14, 0, 0, tzinfo=timezone.utc)

    zones = load_zones(layout_path, store_id)
    tracker = Tracker()

    # Track per-visitor zone dwell for ZONE_DWELL emission
    zone_dwell_start: dict[str, tuple[str, float]] = {}  # visitor_id → (zone_id, start_sec)
    last_dwell_emit: dict[str, float] = {}               # visitor_id → last emit time

    # Track entry-zone presence for ENTRY/EXIT detection
    in_entry_zone: dict[str, bool] = {}

    # Queue depth: count of visitors in billing zone simultaneously
    events_out = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        if frame_idx % FRAME_SKIP != 0:
            continue

        frame_time_sec = frame_idx / fps
        results = model(frame, verbose=False, classes=[0])  # class 0 = person

        detections = []
        for box in results[0].boxes:
            conf = float(box.conf[0])
            if conf < CONF_THRESHOLD:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            bbox_h = y2 - y1
            is_staff = bbox_h > frame_h * STAFF_HEIGHT_FRACTION
            detections.append({"bbox": [x1, y1, x2, y2], "is_staff": is_staff,
                                "confidence": conf})

        track_results = tracker.update(detections, frame, frame_time_sec)

        # Count visitors in billing zone for queue_depth
        billing_count = 0
        for track, _, _ in track_results:
            cx, cy = _centroid(track.bbox)
            from emit import _classify_zone
            zone = _classify_zone(cx, cy, frame_h, frame_w, zones)
            if zone in BILLING_ZONES:
                billing_count += 1

        for det, (track, is_new, is_reentry) in zip(detections, track_results):
            conf = det["confidence"]
            cx, cy = _centroid(track.bbox)
            from emit import _classify_zone
            zone = _classify_zone(cx, cy, frame_h, frame_w, zones)

            # ENTRY / EXIT via entry-zone crossing
            was_in_entry = in_entry_zone.get(track.visitor_id, False)
            now_in_entry = _is_entry_zone(cy, frame_h)

            if is_new or is_reentry:
                evt_type = "REENTRY" if is_reentry else "ENTRY"
                events_out.append(build_event(
                    track, evt_type, store_id, camera_id,
                    clip_start, frame_time_sec, frame_h, frame_w,
                    zones, conf,
                ))
            elif was_in_entry and not now_in_entry:
                # Moved away from entry → entered store
                events_out.append(build_event(
                    track, "ENTRY", store_id, camera_id,
                    clip_start, frame_time_sec, frame_h, frame_w,
                    zones, conf,
                ))
            elif not was_in_entry and now_in_entry:
                # Moved back to entry → exiting
                events_out.append(build_event(
                    track, "EXIT", store_id, camera_id,
                    clip_start, frame_time_sec, frame_h, frame_w,
                    zones, conf,
                ))

            in_entry_zone[track.visitor_id] = now_in_entry

            # ZONE_ENTER / ZONE_EXIT
            prev_zone = track.last_zone
            if zone != prev_zone:
                if prev_zone:
                    events_out.append(build_event(
                        track, "ZONE_EXIT", store_id, camera_id,
                        clip_start, frame_time_sec, frame_h, frame_w,
                        zones, conf,
                    ))
                if zone:
                    events_out.append(build_event(
                        track, "ZONE_ENTER", store_id, camera_id,
                        clip_start, frame_time_sec, frame_h, frame_w,
                        zones, conf,
                    ))
                    # BILLING_QUEUE_JOIN
                    if zone in BILLING_ZONES and billing_count > 1:
                        events_out.append(build_event(
                            track, "BILLING_QUEUE_JOIN", store_id, camera_id,
                            clip_start, frame_time_sec, frame_h, frame_w,
                            zones, conf, queue_depth=billing_count,
                        ))
                    zone_dwell_start[track.visitor_id] = (zone, frame_time_sec)
                    last_dwell_emit[track.visitor_id] = frame_time_sec
                track.last_zone = zone

            # ZONE_DWELL every 30s
            if zone and track.visitor_id in zone_dwell_start:
                dwell_zone, dwell_start = zone_dwell_start[track.visitor_id]
                if dwell_zone == zone:
                    elapsed = frame_time_sec - dwell_start
                    last_emit = last_dwell_emit.get(track.visitor_id, dwell_start)
                    if elapsed >= DWELL_EMIT_INTERVAL and (frame_time_sec - last_emit) >= DWELL_EMIT_INTERVAL:
                        events_out.append(build_event(
                            track, "ZONE_DWELL", store_id, camera_id,
                            clip_start, frame_time_sec, frame_h, frame_w,
                            zones, conf,
                        ))
                        last_dwell_emit[track.visitor_id] = frame_time_sec

        # Emit EXIT for tracks that disappeared
        for track in tracker.exited:
            if track.visitor_id in in_entry_zone:
                events_out.append(build_event(
                    track, "EXIT", store_id, camera_id,
                    clip_start, frame_time_sec, frame_h, frame_w,
                    zones, conf=0.5,
                ))
                # BILLING_QUEUE_ABANDON if they were in billing
                if track.last_zone in BILLING_ZONES:
                    events_out.append(build_event(
                        track, "BILLING_QUEUE_ABANDON", store_id, camera_id,
                        clip_start, frame_time_sec, frame_h, frame_w,
                        zones, conf=0.5,
                    ))
                del in_entry_zone[track.visitor_id]

    cap.release()

    with open(output_file, "a") as f:
        for ev in events_out:
            f.write(json.dumps(ev) + "\n")

    print(f"  {camera_id}: {len(events_out)} events written")
    return len(events_out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos",  default="dataset/videos")
    parser.add_argument("--layout",  default="dataset/layouts/store_layout.json")
    parser.add_argument("--store",   default="STORE_001")
    parser.add_argument("--output",  default="data/events/events.jsonl")
    parser.add_argument("--model",   default="yolov8n.pt")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    # Clear output file
    open(args.output, "w").close()

    model = YOLO(args.model)
    total = 0

    for fname in sorted(os.listdir(args.videos)):
        if not fname.lower().endswith(".mp4"):
            continue
        camera_id = os.path.splitext(fname)[0].replace(" ", "_").upper()
        video_path = os.path.join(args.videos, fname)
        print(f"Processing {fname} → {camera_id}")
        total += detect_video(
            video_path, args.store, camera_id,
            args.layout, args.output, model,
        )

    print(f"\nTotal events: {total} → {args.output}")


if __name__ == "__main__":
    main()
