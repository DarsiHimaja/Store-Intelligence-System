"""
Tracker: assigns persistent visitor_ids across frames using IoU overlap
and a simple appearance-based Re-ID via histogram distance.

Re-entry detection: if a visitor_id that previously EXITed re-appears
within RE_ENTRY_WINDOW_SEC seconds, it is flagged as REENTRY.
"""
import uuid
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

IOU_THRESHOLD = 0.3
MAX_LOST_FRAMES = 30          # frames before a track is dropped
RE_ENTRY_WINDOW_SEC = 120     # seconds; re-appearance within this = REENTRY


@dataclass
class Track:
    visitor_id: str
    bbox: list          # [x1, y1, x2, y2]
    hist: Optional[np.ndarray]
    lost: int = 0
    is_staff: bool = False
    entry_frame: int = 0
    last_zone: Optional[str] = None
    session_seq: int = 0
    exited: bool = False
    exit_time: Optional[float] = None   # wall-clock seconds


def _iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


def _color_hist(frame, bbox, bins=32):
    x1, y1, x2, y2 = [int(v) for v in bbox]
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    hist = np.concatenate([
        np.histogram(crop[:, :, c], bins=bins, range=(0, 256))[0]
        for c in range(min(3, crop.shape[2]))
    ]).astype(np.float32)
    norm = np.linalg.norm(hist)
    return hist / norm if norm > 0 else hist


def _hist_dist(h1, h2):
    if h1 is None or h2 is None:
        return 1.0
    return float(np.linalg.norm(h1 - h2))


class Tracker:
    def __init__(self):
        self.active: list[Track] = []
        self.exited: list[Track] = []   # for re-entry matching

    def update(self, detections, frame, frame_time: float):
        """
        detections: list of dicts with keys: bbox, is_staff
        frame: numpy array (H,W,C)
        frame_time: float seconds from clip start

        Returns list of (track, is_new, is_reentry)
        """
        # Build histograms for detections
        det_hists = [_color_hist(frame, d["bbox"]) for d in detections]

        # Match detections to active tracks via IoU
        matched_tracks = set()
        matched_dets = set()
        results = []

        for di, det in enumerate(detections):
            best_iou, best_ti = 0.0, -1
            for ti, track in enumerate(self.active):
                if ti in matched_tracks:
                    continue
                iou = _iou(det["bbox"], track.bbox)
                if iou > best_iou:
                    best_iou, best_ti = iou, ti

            if best_iou >= IOU_THRESHOLD:
                track = self.active[best_ti]
                track.bbox = det["bbox"]
                track.hist = det_hists[di] or track.hist
                track.lost = 0
                track.session_seq += 1
                matched_tracks.add(best_ti)
                matched_dets.add(di)
                results.append((track, False, False))

        # Unmatched detections → new tracks (check re-entry first)
        for di, det in enumerate(detections):
            if di in matched_dets:
                continue
            hist = det_hists[di]
            reentry_track = self._match_exited(hist, frame_time)
            if reentry_track:
                reentry_track.bbox = det["bbox"]
                reentry_track.hist = hist or reentry_track.hist
                reentry_track.lost = 0
                reentry_track.exited = False
                reentry_track.session_seq += 1
                self.active.append(reentry_track)
                self.exited.remove(reentry_track)
                results.append((reentry_track, False, True))
            else:
                new_track = Track(
                    visitor_id=f"VIS_{uuid.uuid4().hex[:8]}",
                    bbox=det["bbox"],
                    hist=hist,
                    is_staff=det.get("is_staff", False),
                    entry_frame=int(frame_time),
                    session_seq=1,
                )
                self.active.append(new_track)
                results.append((new_track, True, False))

        # Increment lost counter for unmatched active tracks
        for ti, track in enumerate(self.active):
            if ti not in matched_tracks and not any(t is track for t, _, _ in results):
                track.lost += 1

        # Retire lost tracks
        still_active = []
        for track in self.active:
            if track.lost > MAX_LOST_FRAMES:
                track.exited = True
                track.exit_time = frame_time
                self.exited.append(track)
            else:
                still_active.append(track)
        self.active = still_active

        # Prune old exited tracks
        self.exited = [
            t for t in self.exited
            if t.exit_time and (frame_time - t.exit_time) < RE_ENTRY_WINDOW_SEC
        ]

        return results

    def _match_exited(self, hist, frame_time: float) -> Optional[Track]:
        best_dist, best_track = 0.5, None   # threshold
        for track in self.exited:
            if track.exit_time and (frame_time - track.exit_time) > RE_ENTRY_WINDOW_SEC:
                continue
            d = _hist_dist(hist, track.hist)
            if d < best_dist:
                best_dist, best_track = d, track
        return best_track
