"""
pipeline/recovery.py
~~~~~~~~~~~~~~~~~~~~
Triggers and executes re-localisation of a lost object via remote grounding.

Recovery is deliberately expensive (one remote API call per attempt) and
should only be triggered when local detection has genuinely failed, not on
every slightly-weak frame.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from .data_structures import GroundingResult, TrackResult
from .remote_grounding import RemoteGrounding


class Recovery:
    """Triggers and executes recovery via remote grounding.

    Two conditions independently trigger recovery:

    1. The latest confidence is below ``CONFIDENCE_THRESHOLD``.
    2. The last ``LOST_FRAMES_THRESHOLD`` track results are all in the
       ``"lost"`` state.
    """

    CONFIDENCE_THRESHOLD: float = 0.35
    LOST_FRAMES_THRESHOLD: int = 5

    def __init__(self, remote_grounding: RemoteGrounding) -> None:
        self._grounding = remote_grounding

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_recover(
        self, track_result: TrackResult, history: list[TrackResult]
    ) -> bool:
        """Decide whether a recovery attempt should be made.

        Parameters
        ----------
        track_result:
            The most recent ``TrackResult``.
        history:
            Recent track history (newest last).  May be empty.

        Returns
        -------
        bool
            *True* if recovery is recommended.
        """
        # Condition 1: current confidence is too low
        if track_result.confidence < self.CONFIDENCE_THRESHOLD:
            return True

        # Condition 2: last N consecutive frames are all "lost"
        if len(history) >= self.LOST_FRAMES_THRESHOLD:
            recent = history[-self.LOST_FRAMES_THRESHOLD :]
            if all(r.state == "lost" for r in recent):
                return True

        return False

    def recover(
        self, frame: np.ndarray, query: str
    ) -> Optional[GroundingResult]:
        """Attempt to re-localise the object in *frame*.

        Parameters
        ----------
        frame:
            Current camera frame.
        query:
            Natural-language description of the enrolled object.

        Returns
        -------
        GroundingResult | None
            The new grounding result, or *None* if the remote service failed.
        """
        return self._grounding.ground_object(frame, query)
