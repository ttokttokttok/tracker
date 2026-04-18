"""
pipeline/frame_ingestion.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Manages a fixed-size camera frame buffer with timestamp tracking.
"""

from __future__ import annotations

import time
from collections import deque

import numpy as np


class FrameIngestion:
    """Manages camera frame buffer.

    Frames are stored as (frame, timestamp) tuples in a fixed-size deque.
    When the buffer is full the oldest frame is automatically evicted.
    """

    def __init__(self, max_buffer: int = 30) -> None:
        self._max_buffer = max_buffer
        self._buffer: deque[tuple[np.ndarray, float]] = deque(maxlen=max_buffer)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ingest(self, frame: np.ndarray, timestamp: float | None = None) -> float:
        """Push a new frame into the buffer.

        Parameters
        ----------
        frame:
            BGR image array with shape (H, W, 3).
        timestamp:
            Unix timestamp in seconds.  Uses ``time.time()`` when *None*.

        Returns
        -------
        float
            The timestamp that was recorded for this frame.
        """
        if timestamp is None:
            timestamp = time.time()
        self._buffer.append((frame.copy(), timestamp))
        return timestamp

    def get_latest_frame(self) -> tuple[np.ndarray, float] | None:
        """Return the most recently ingested (frame, timestamp) pair.

        Returns *None* if the buffer is empty.
        """
        if not self._buffer:
            return None
        return self._buffer[-1]

    def get_recent_frames(self, count: int) -> list[tuple[np.ndarray, float]]:
        """Return the *count* most recent frames, newest last.

        If fewer than *count* frames are available all buffered frames are
        returned.
        """
        frames = list(self._buffer)
        return frames[-count:] if count < len(frames) else frames

    # ------------------------------------------------------------------
    # Introspection helpers (useful for tests)
    # ------------------------------------------------------------------

    def buffer_size(self) -> int:
        """Number of frames currently held in the buffer."""
        return len(self._buffer)

    def clear(self) -> None:
        """Flush the entire frame buffer."""
        self._buffer.clear()
