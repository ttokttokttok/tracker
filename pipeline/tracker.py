"""
pipeline/tracker.py
~~~~~~~~~~~~~~~~~~~
Smooths per-frame detection results over time using an exponential moving
average (EMA) on the bounding-box coordinates.

When the detector returns "lost", the tracker holds the last known position
rather than blending toward [0,0,0,0].
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from .data_structures import DetectionResult, TrackResult


class Tracker:
    ALPHA: float = 0.4          # smoothing factor (higher = more reactive)
    MAX_LOST_FRAMES: int = 10   # frames before confidence decays to zero

    def __init__(self) -> None:
        self._smoothed_bbox: Optional[list[float]] = None
        self._last_good_bbox: Optional[list[float]] = None
        self._initialized: bool = False
        self._lost_frames: int = 0
        self._last_confidence: float = 0.0

    def start(self, initial_bbox: list[int]) -> None:
        self._smoothed_bbox = [float(v) for v in initial_bbox]
        self._last_good_bbox = self._smoothed_bbox[:]
        self._initialized = True
        self._lost_frames = 0

    def update(self, detection_result: DetectionResult) -> TrackResult:
        is_lost = detection_result.state == "lost" or detection_result.bbox == [0, 0, 0, 0]

        if not self._initialized or self._smoothed_bbox is None:
            if is_lost:
                # Nothing to seed from yet
                return TrackResult(
                    bbox=[0, 0, 0, 0],
                    smoothed_bbox=[0, 0, 0, 0],
                    confidence=0.0,
                    state="lost",
                    timestamp=detection_result.timestamp,
                )
            self._smoothed_bbox = [float(v) for v in detection_result.bbox]
            self._last_good_bbox = self._smoothed_bbox[:]
            self._initialized = True
            self._lost_frames = 0

        if is_lost:
            # Hold last known position — do NOT blend toward zero
            self._lost_frames += 1
            # Decay confidence gradually over lost frames
            decay = max(0.0, 1.0 - self._lost_frames / self.MAX_LOST_FRAMES)
            confidence = round(self._last_confidence * decay, 4)
            smoothed_int = [int(round(v)) for v in self._smoothed_bbox]
            state = "lost" if self._lost_frames >= self.MAX_LOST_FRAMES else "weak"
            self._last_confidence = confidence
            return TrackResult(
                bbox=detection_result.bbox,
                smoothed_bbox=smoothed_int,   # hold position
                confidence=confidence,
                state=state,
                timestamp=detection_result.timestamp,
            )

        # Good detection — EMA update
        self._lost_frames = 0
        self._smoothed_bbox = [
            self.ALPHA * float(new) + (1.0 - self.ALPHA) * prev
            for new, prev in zip(detection_result.bbox, self._smoothed_bbox)
        ]
        self._last_good_bbox = self._smoothed_bbox[:]
        self._last_confidence = detection_result.confidence

        smoothed_int = [int(round(v)) for v in self._smoothed_bbox]
        state = self._detection_state_to_track_state(detection_result.state)

        return TrackResult(
            bbox=detection_result.bbox,
            smoothed_bbox=smoothed_int,
            confidence=detection_result.confidence,
            state=state,
            timestamp=detection_result.timestamp,
        )

    def get_current_bbox(self) -> list[int] | None:
        if self._smoothed_bbox is None:
            return None
        return [int(round(v)) for v in self._smoothed_bbox]

    def reset(self) -> None:
        self._smoothed_bbox = None
        self._last_good_bbox = None
        self._initialized = False
        self._lost_frames = 0
        self._last_confidence = 0.0

    @staticmethod
    def _detection_state_to_track_state(detection_state: str) -> str:
        return {"detected": "tracking", "weak": "weak", "lost": "lost"}.get(detection_state, "lost")
