"""
pipeline/remote_grounding.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Stub remote vision grounding.

IMPORTANT: This module must only be called during enrollment and recovery,
NOT on every tracking frame, because of its simulated latency (~100 ms per
call).  The local detector handles per-frame inference.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

import numpy as np

from .data_structures import GroundingResult


class RemoteGrounding:
    """Stub remote vision grounding.

    The mock implementation:
    - Detects a plausible centre-region bounding box with small random noise.
    - Simulates ~80 % success rate.
    - Adds ~100 ms of simulated network + inference latency.

    In production this class would be replaced by a real API call (e.g. to a
    vision-language model such as Florence-2 or GPT-4V).
    """

    # Fraction of calls that succeed (the rest return None)
    _SUCCESS_RATE: float = 0.80
    # Simulated latency in seconds
    _LATENCY: float = 0.10
    # Maximum pixel noise added to the bbox
    _BBOX_NOISE: int = 20

    def __init__(self, provider: str = "mock") -> None:
        self.provider = provider
        self._call_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ground_object(
        self, frame: np.ndarray, query: str
    ) -> GroundingResult | None:
        """Locate *query* inside *frame*.

        Parameters
        ----------
        frame:
            BGR image with shape (H, W, 3).
        query:
            Natural-language description of the object to find.

        Returns
        -------
        GroundingResult | None
            Detection result, or *None* on simulated failure.
        """
        self._call_count += 1

        # Simulate network / inference latency
        time.sleep(self._LATENCY)

        # Simulate occasional failures
        if random.random() > self._SUCCESS_RATE:
            return None

        h, w = frame.shape[:2]

        # Place the bounding box in the centre ~40 % of the image with noise
        cx = w // 2 + random.randint(-self._BBOX_NOISE, self._BBOX_NOISE)
        cy = h // 2 + random.randint(-self._BBOX_NOISE, self._BBOX_NOISE)
        bw = max(40, w // 4 + random.randint(-self._BBOX_NOISE, self._BBOX_NOISE))
        bh = max(40, h // 4 + random.randint(-self._BBOX_NOISE, self._BBOX_NOISE))

        # Clamp so the box stays inside the frame
        x = max(0, cx - bw // 2)
        y = max(0, cy - bh // 2)
        bw = min(bw, w - x)
        bh = min(bh, h - y)

        confidence = round(random.uniform(0.55, 0.95), 3)

        return GroundingResult(
            label=query,
            query=query,
            bbox=[x, y, bw, bh],
            confidence=confidence,
            timestamp=time.time(),
            provider=self.provider,
        )

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    @property
    def call_count(self) -> int:
        """Total number of ``ground_object`` calls made so far."""
        return self._call_count

    def reset_call_count(self) -> None:
        """Reset the call counter (useful in tests)."""
        self._call_count = 0
