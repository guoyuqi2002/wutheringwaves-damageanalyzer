from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Optional

from config import (
    MAX_DAMAGE_VALUE,
    MIN_DAMAGE_VALUE,
    MIN_DETECTION_CONFIDENCE,
    OVERLAP_IOU_THRESHOLD,
    POSITION_MATCH_DISTANCE,
    STABLE_FRAME_COUNT,
    TRACK_TTL,
)


@dataclass
class _Track:
    value: int
    box: list[int]
    confidence: float
    first_seen: float
    last_seen: float
    stable_count: int = 1
    counted: bool = False
    unknown: bool = False


@dataclass
class _SlotStats:
    damage: int = 0
    active_seconds: float = 0.0


class DamageTracker:
    """Tracks damage detections across frames and counts each stable number once."""

    def __init__(self) -> None:
        self.total_damage = 0
        self.unknown_count = 0
        self.active_slot = 1
        self.slot_stats = {slot: _SlotStats() for slot in (1, 2, 3)}
        self._tracks: list[_Track] = []
        self._combat_started_at: Optional[float] = None
        self._last_stats_at = time.monotonic()

    def update(self, detections: list[dict]) -> dict:
        now = time.monotonic()
        self._update_active_time(now)
        valid_detections = self._filter_detections(detections)
        self._mark_overlaps_unknown(valid_detections)

        for detection in valid_detections:
            track = self._find_match(detection)
            if track is None:
                self._tracks.append(
                    _Track(
                        value=int(detection["value"]),
                        box=list(detection["box"]),
                        confidence=float(detection["confidence"]),
                        first_seen=now,
                        last_seen=now,
                        unknown=bool(detection.get("unknown", False)),
                    )
                )
                continue

            track.box = list(detection["box"])
            track.confidence = max(track.confidence, float(detection["confidence"]))
            track.last_seen = now
            track.stable_count += 1
            track.unknown = track.unknown or bool(detection.get("unknown", False))

        for track in self._tracks:
            if track.counted or track.stable_count < STABLE_FRAME_COUNT:
                continue

            track.counted = True
            if track.unknown:
                self.unknown_count += 1
            else:
                self.total_damage += track.value
                self.slot_stats[self.active_slot].damage += track.value
                if self._combat_started_at is None:
                    self._combat_started_at = now

        self._tracks = [
            track for track in self._tracks if now - track.last_seen <= TRACK_TTL
        ]

        return self.stats(now)

    def reset(self) -> None:
        self.total_damage = 0
        self.unknown_count = 0
        self.active_slot = 1
        self.slot_stats = {slot: _SlotStats() for slot in (1, 2, 3)}
        self._tracks.clear()
        self._combat_started_at = None
        self._last_stats_at = time.monotonic()

    def set_active_slot(self, slot: int) -> None:
        if slot not in self.slot_stats:
            raise ValueError("slot must be 1, 2, or 3")

        now = time.monotonic()
        self._update_active_time(now)
        self.active_slot = slot

    def stats(self, now: Optional[float] = None) -> dict:
        current_time = now or time.monotonic()
        self._update_active_time(current_time)
        elapsed = 0.0
        if self._combat_started_at is not None:
            elapsed = max(0.0, current_time - self._combat_started_at)

        dps = self.total_damage / elapsed if elapsed > 0 else 0.0
        slots = {}
        for slot, slot_stats in self.slot_stats.items():
            slot_dps = (
                slot_stats.damage / slot_stats.active_seconds
                if slot_stats.active_seconds > 0
                else 0.0
            )
            percent = (
                slot_stats.damage / self.total_damage * 100
                if self.total_damage > 0
                else 0.0
            )
            slots[slot] = {
                "damage": slot_stats.damage,
                "active_seconds": slot_stats.active_seconds,
                "dps": slot_dps,
                "percent": percent,
            }

        return {
            "total_damage": self.total_damage,
            "dps": dps,
            "elapsed_time": elapsed,
            "unknown": self.unknown_count,
            "active_tracks": len(self._tracks),
            "active_slot": self.active_slot,
            "slots": slots,
        }

    def _update_active_time(self, now: float) -> None:
        delta = max(0.0, now - self._last_stats_at)
        self.slot_stats[self.active_slot].active_seconds += delta
        self._last_stats_at = now

    def _filter_detections(self, detections: list[dict]) -> list[dict]:
        valid = []
        for detection in detections:
            try:
                value = int(detection["value"])
                box = [int(part) for part in detection["box"]]
                confidence = float(detection.get("confidence", 0.0))
            except (KeyError, TypeError, ValueError):
                continue

            if len(box) != 4:
                continue
            if not (MIN_DAMAGE_VALUE <= value <= MAX_DAMAGE_VALUE):
                continue
            if confidence < MIN_DETECTION_CONFIDENCE:
                continue
            if box[2] <= 0 or box[3] <= 0:
                continue

            valid.append(
                {
                    "value": value,
                    "box": box,
                    "confidence": confidence,
                    "unknown": bool(detection.get("unknown", False)),
                }
            )
        return valid

    def _find_match(self, detection: dict) -> Optional[_Track]:
        candidates = [
            track
            for track in self._tracks
            if track.value == detection["value"]
            and self._center_distance(track.box, detection["box"])
            <= POSITION_MATCH_DISTANCE
        ]
        if not candidates:
            return None

        return min(
            candidates,
            key=lambda track: self._center_distance(track.box, detection["box"]),
        )

    def _mark_overlaps_unknown(self, detections: list[dict]) -> None:
        for index, left in enumerate(detections):
            for right in detections[index + 1 :]:
                if self._iou(left["box"], right["box"]) >= OVERLAP_IOU_THRESHOLD:
                    left["unknown"] = True
                    right["unknown"] = True

    def _center_distance(self, left: list[int], right: list[int]) -> float:
        left_x = left[0] + left[2] / 2
        left_y = left[1] + left[3] / 2
        right_x = right[0] + right[2] / 2
        right_y = right[1] + right[3] / 2
        return math.hypot(left_x - right_x, left_y - right_y)

    def _iou(self, left: list[int], right: list[int]) -> float:
        left_x1, left_y1, left_w, left_h = left
        right_x1, right_y1, right_w, right_h = right
        left_x2 = left_x1 + left_w
        left_y2 = left_y1 + left_h
        right_x2 = right_x1 + right_w
        right_y2 = right_y1 + right_h

        inter_x1 = max(left_x1, right_x1)
        inter_y1 = max(left_y1, right_y1)
        inter_x2 = min(left_x2, right_x2)
        inter_y2 = min(left_y2, right_y2)

        inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
        left_area = left_w * left_h
        right_area = right_w * right_h
        union_area = left_area + right_area - inter_area
        return inter_area / union_area if union_area > 0 else 0.0
