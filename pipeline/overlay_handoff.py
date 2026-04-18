"""
pipeline/overlay_handoff.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Exposes the latest tracking bbox for downstream consumers (e.g. a renderer or
AR overlay).  No rendering is performed here; this module is a pure data
handoff point.
"""

from __future__ import annotations

from typing import Optional

from .data_structures import TrackResult


class OverlayHandoff:
    """Exposes the latest bbox for a future renderer.

    A renderer, AR overlay, or any other consumer polls ``get_latest_bbox()``
    at its own cadence.  This decouples the pipeline frame rate from the
    rendering frame rate.
    """

    def __init__(self) -> None:
        self._latest: Optional[TrackResult] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit_bbox(self, track_result: TrackResult) -> None:
        """Store the latest tracking result for downstream consumption.

        Parameters
        ----------
        track_result:
            The most recent output of ``Tracker.update()``.
        """
        self._latest = track_result

    def get_latest_bbox(self) -> Optional[TrackResult]:
        """Return the most recently emitted ``TrackResult``, or *None*."""
        return self._latest
