"""
pipeline/yolo_grounding.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Real local grounding using YOLOv8.  Drop-in replacement for RemoteGrounding.

Used ONLY during enrollment and recovery — not on every tracking frame.
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from .data_structures import GroundingResult

# COCO class names that map to common user labels
_LABEL_MAP: dict[str, list[str]] = {
    "can":      ["bottle", "cup", "vase"],
    "cup":      ["cup", "bottle"],
    "bottle":   ["bottle"],
    "laptop":   ["laptop"],
    "monitor":  ["tv", "laptop"],
    "tv":       ["tv"],
    "phone":    ["cell phone"],
    "book":     ["book"],
    "box":      ["suitcase", "backpack"],
    "bag":      ["handbag", "backpack", "suitcase"],
    "bowl":     ["bowl"],
    "mouse":    ["mouse"],
    "keyboard": ["keyboard"],
    "chair":    ["chair"],
    "person":   ["person"],
}


class YOLOGrounding:
    """Local object grounding using YOLOv8n (nano — fast, ~6 MB).

    Falls back to the largest detection if the label isn't in the map.
    """

    def __init__(self, model_size: str = "yolov8n.pt", confidence: float = 0.25) -> None:
        from ultralytics import YOLO  # imported lazily so non-YOLO paths don't break
        self._model = YOLO(model_size)
        self._min_conf = confidence
        self._call_count = 0
        self.provider = "yolov8"

    def ground_object(self, frame: np.ndarray, query: str) -> Optional[GroundingResult]:
        """Run YOLO on *frame* and return the best bbox matching *query*."""
        self._call_count += 1

        results = self._model(frame, verbose=False)[0]
        if results.boxes is None or len(results.boxes) == 0:
            return None

        # Build candidate list: (confidence, bbox_xyxy, class_name)
        candidates = []
        names = results.names
        for box in results.boxes:
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            cls_name = names[cls_id].lower()
            if conf >= self._min_conf:
                xyxy = box.xyxy[0].tolist()
                candidates.append((conf, xyxy, cls_name))

        if not candidates:
            return None

        # Filter by mapped labels — no fallback to random objects
        target_classes = _LABEL_MAP.get(query.lower().strip())
        if target_classes:
            matched = [c for c in candidates if c[2] in target_classes]
        else:
            matched = candidates  # unknown label: use all detections

        if not matched:
            return None

        # Reject detections that cover more than 40% of the frame (probably wrong object)
        h, w = frame.shape[:2]
        frame_area = h * w
        matched = [
            c for c in matched
            if ((c[1][2] - c[1][0]) * (c[1][3] - c[1][1])) / frame_area < 0.40
        ]

        if not matched:
            return None

        best = max(matched, key=lambda c: c[0])

        conf, xyxy, cls_name = best
        x1, y1, x2, y2 = xyxy
        x, y, w, h = int(x1), int(y1), int(x2 - x1), int(y2 - y1)

        return GroundingResult(
            label=cls_name,
            query=query,
            bbox=[x, y, w, h],
            confidence=round(conf, 3),
            timestamp=time.time(),
            provider=self.provider,
        )

    def detect_all(self, frame: np.ndarray, min_conf: float = 0.30) -> list[dict]:
        """Return all YOLO detections above min_conf (for display purposes)."""
        results = self._model(frame, verbose=False)[0]
        out = []
        if results.boxes is None:
            return out
        h, w = frame.shape[:2]
        frame_area = h * w
        for box in results.boxes:
            conf = float(box.conf[0])
            if conf < min_conf:
                continue
            cls_name = results.names[int(box.cls[0])].lower()
            xyxy = box.xyxy[0].tolist()
            bx = int(xyxy[0]); by = int(xyxy[1])
            bw = int(xyxy[2] - xyxy[0]); bh = int(xyxy[3] - xyxy[1])
            area_ratio = (bw * bh) / frame_area
            out.append({
                "label": cls_name,
                "bbox": [bx, by, bw, bh],
                "confidence": round(conf, 3),
                "area_ratio": round(area_ratio, 3),
            })
        return sorted(out, key=lambda d: d["confidence"], reverse=True)

    @property
    def call_count(self) -> int:
        return self._call_count
