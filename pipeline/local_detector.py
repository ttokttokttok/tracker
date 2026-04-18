"""
pipeline/local_detector.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Per-frame object detection using YOLOv8 (local, fast).

Uses the same YOLOGrounding model already loaded during enrollment so there
is no extra model weight. Falls back to template matching if YOLO is not
available.
"""

from __future__ import annotations

import time
from typing import Optional

import cv2
import numpy as np

from .data_structures import DetectionResult, Reference


class LocalDetector:
    """Per-frame detection via YOLO (preferred) or template matching (fallback).

    Call initialize() with the enrolled reference set AND optionally the
    YOLOGrounding instance.  When YOLO is available it runs inference on every
    frame and filters by the enrolled label — fast (~30 ms on CPU for YOLOv8n).
    """

    _THRESH_DETECTED: float = 0.55
    _THRESH_WEAK: float = 0.40

    def __init__(self) -> None:
        self._references: list[Reference] = []
        self._initialized: bool = False
        self._grounding = None   # YOLOGrounding instance, set via initialize()
        self._query: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(
        self,
        reference_set: list[Reference],
        grounding=None,
        query: str = "",
    ) -> None:
        """Load references and optionally the grounding model for per-frame use."""
        self._references = reference_set
        self._initialized = bool(reference_set)
        self._grounding = grounding
        self._query = query

    def detect(self, frame: np.ndarray) -> DetectionResult:
        now = time.time()

        if not self._initialized:
            return DetectionResult(bbox=[0, 0, 0, 0], confidence=0.0, state="lost", timestamp=now)

        if self._grounding is not None:
            return self._detect_yolo(frame, now)
        return self._detect_template(frame, now)

    def reset(self) -> None:
        self._references = []
        self._initialized = False
        self._grounding = None
        self._query = ""

    # ------------------------------------------------------------------
    # YOLO-based detection (preferred)
    # ------------------------------------------------------------------

    def _detect_yolo(self, frame: np.ndarray, now: float) -> DetectionResult:
        result = self._grounding.ground_object(frame, self._query)

        if result is None:
            return DetectionResult(bbox=[0, 0, 0, 0], confidence=0.0, state="lost", timestamp=now)

        state = self._confidence_to_state(result.confidence)
        return DetectionResult(
            bbox=result.bbox,
            confidence=round(result.confidence, 4),
            state=state,
            timestamp=now,
        )

    # ------------------------------------------------------------------
    # Template-matching fallback
    # ------------------------------------------------------------------

    def _detect_template(self, frame: np.ndarray, now: float) -> DetectionResult:
        best_bbox: list[int] = [0, 0, 0, 0]
        scores: list[float] = []

        for ref in self._references:
            bbox, score = self._match_single_reference(frame, ref)
            scores.append(score)
            if score == max(scores):
                best_bbox = bbox

        confidence = float(np.mean(scores)) if scores else 0.0
        state = self._confidence_to_state(confidence)

        return DetectionResult(
            bbox=best_bbox,
            confidence=round(confidence, 4),
            state=state,
            timestamp=now,
        )

    def _match_single_reference(
        self, frame: np.ndarray, ref: Reference
    ) -> tuple[list[int], float]:
        template = self._decode_crop(ref.crop_bytes)
        t_h, t_w = template.shape[:2]
        f_h, f_w = frame.shape[:2]

        if t_h >= f_h or t_w >= f_w:
            scale = min((f_h - 1) / t_h, (f_w - 1) / t_w) * 0.9
            template = cv2.resize(template, (max(1, int(t_w * scale)), max(1, int(t_h * scale))))
            t_h, t_w = template.shape[:2]

        result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        score = float(np.clip(max_val, 0.0, 1.0))
        x, y = max_loc
        return [x, y, t_w, t_h], score

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _confidence_to_state(self, confidence: float) -> str:
        if confidence > self._THRESH_DETECTED:
            return "detected"
        if confidence > self._THRESH_WEAK:
            return "weak"
        return "lost"

    @staticmethod
    def _decode_crop(data: bytes) -> np.ndarray:
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError("Failed to decode reference crop bytes.")
        return img
