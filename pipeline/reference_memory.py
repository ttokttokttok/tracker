"""
pipeline/reference_memory.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Stores 3-5 distinct reference crops for enrolled objects.

Near-duplicate frames are rejected using OpenCV histogram correlation so that
the final reference set provides genuine viewpoint diversity.
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .data_structures import Reference


class ReferenceMemory:
    """Stores 3-5 distinct reference crops, rejecting near-duplicates.

    Duplicate detection uses the OpenCV histogram comparison with the
    CORREL method (range [-1, 1]; 1 = identical).  Any candidate whose
    similarity to an already-stored crop exceeds ``DUPLICATE_THRESHOLD``
    is rejected.
    """

    MAX_REFS: int = 5
    DUPLICATE_THRESHOLD: float = 0.85

    # Context padding added around the tight crop (fraction of each side)
    _CONTEXT_PAD: float = 0.30

    def __init__(self, storage_dir: str = "refs") -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._references: list[Reference] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_reference(
        self,
        frame: np.ndarray,
        bbox: list[int],
        timestamp: float,
        view_hint: str = "",
    ) -> Optional[Reference]:
        """Extract and store a reference crop from *frame* at *bbox*.

        Parameters
        ----------
        frame:
            Full BGR camera frame.
        bbox:
            Bounding box ``[x, y, w, h]`` of the object within *frame*.
        timestamp:
            Frame capture time (Unix seconds).
        view_hint:
            Human-readable hint describing the viewpoint (e.g. "left side").

        Returns
        -------
        Reference | None
            The newly created reference, or *None* if the crop was a duplicate
            or the storage is already full.
        """
        if len(self._references) >= self.MAX_REFS:
            return None

        crop = self._extract_crop(frame, bbox)
        if crop is None or crop.size == 0:
            return None

        if self.is_duplicate(crop):
            return None

        context_crop = self._extract_context_crop(frame, bbox)

        ref_id = str(uuid.uuid4())[:8]
        crop_bytes = self._encode(crop)
        context_bytes = self._encode(context_crop) if context_crop is not None else None

        ref = Reference(
            id=ref_id,
            frame_ts=timestamp,
            bbox=bbox,
            crop_bytes=crop_bytes,
            context_crop_bytes=context_bytes,
            view_hint=view_hint,
        )
        self._references.append(ref)
        return ref

    def get_references(self) -> list[Reference]:
        """Return all stored references (read-only view)."""
        return list(self._references)

    def count_references(self) -> int:
        """Number of references currently stored."""
        return len(self._references)

    def is_duplicate(self, candidate_crop: np.ndarray) -> bool:
        """Return *True* if *candidate_crop* is too similar to an existing ref.

        Uses the OpenCV histogram CORREL method.  Similarity > ``DUPLICATE_THRESHOLD``
        is considered a duplicate.
        """
        if not self._references:
            return False

        candidate_hist = self._compute_hist(candidate_crop)

        for ref in self._references:
            stored_crop = self._decode(ref.crop_bytes)
            stored_hist = self._compute_hist(stored_crop)
            similarity = cv2.compareHist(candidate_hist, stored_hist, cv2.HISTCMP_CORREL)
            if similarity > self.DUPLICATE_THRESHOLD:
                return True

        return False

    def build_reference_set(self) -> list[Reference]:
        """Return all references suitable for initialising the local detector."""
        return list(self._references)

    def clear(self) -> None:
        """Remove all stored references."""
        self._references.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_crop(frame: np.ndarray, bbox: list[int]) -> Optional[np.ndarray]:
        """Crop the tight object region from *frame*."""
        x, y, w, h = bbox
        h_frame, w_frame = frame.shape[:2]
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(w_frame, x + w)
        y2 = min(h_frame, y + h)
        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2].copy()

    @classmethod
    def _extract_context_crop(
        cls, frame: np.ndarray, bbox: list[int]
    ) -> Optional[np.ndarray]:
        """Crop a padded region around the object for context."""
        x, y, w, h = bbox
        pad_x = int(w * cls._CONTEXT_PAD)
        pad_y = int(h * cls._CONTEXT_PAD)
        h_frame, w_frame = frame.shape[:2]
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w_frame, x + w + pad_x)
        y2 = min(h_frame, y + h + pad_y)
        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2].copy()

    @staticmethod
    def _compute_hist(crop: np.ndarray) -> np.ndarray:
        """Compute a normalised HSV histogram for *crop*."""
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        return hist

    @staticmethod
    def _encode(image: np.ndarray) -> bytes:
        """Encode an image array to PNG bytes."""
        ok, buf = cv2.imencode(".png", image)
        if not ok:
            raise RuntimeError("cv2.imencode failed")
        return buf.tobytes()

    @staticmethod
    def _decode(data: bytes) -> np.ndarray:
        """Decode PNG bytes back to an image array."""
        arr = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
