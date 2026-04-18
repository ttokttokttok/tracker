"""
pipeline/enrollment_guide.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Guides the user through a multi-view enrollment session, similar to the
multi-angle face enrollment found on modern smartphones.
"""

from __future__ import annotations

import time
from typing import Optional

import numpy as np

from .data_structures import EnrollmentFeedback
from .reference_memory import ReferenceMemory
from .remote_grounding import RemoteGrounding


class EnrollmentGuide:
    """Guides user through multi-view enrollment like face enrollment.

    The guide requests the remote grounding service to locate the target
    object in each candidate frame, then asks ``ReferenceMemory`` to store
    the crop.  Duplicate crops are silently skipped so the caller only needs
    to keep feeding frames until ``is_enrollment_complete()`` returns *True*.
    """

    TARGET_CROPS: int = 5
    MIN_CROPS: int = 3

    # Cyclic guidance hints shown to the user
    _GUIDANCE_ROTATION: list[str] = [
        "hold steady",
        "move closer",
        "show left side",
        "show right side",
        "tilt slightly",
        "move back",
        "show top",
    ]

    def __init__(
        self,
        reference_memory: ReferenceMemory,
        remote_grounding: RemoteGrounding,
    ) -> None:
        self._memory = reference_memory
        self._grounding = remote_grounding
        self._label: str = ""
        self._started: bool = False
        self._frame_index: int = 0   # total frames analysed (including rejects)
        self._accepted: int = 0      # frames whose crops were stored

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_enrollment(self, object_label: str) -> None:
        """Begin a new enrollment session for *object_label*.

        Resets all internal counters and clears any previously stored
        references (the caller should reset ``ReferenceMemory`` explicitly
        if they want a clean slate before calling this).
        """
        self._label = object_label
        self._started = True
        self._frame_index = 0
        self._accepted = 0

    def analyze_enrollment_frame(
        self, frame: np.ndarray, timestamp: float
    ) -> EnrollmentFeedback:
        """Process a single enrollment frame.

        1. Calls the remote grounding service to locate the object.
        2. If found, tries to add the crop to ``ReferenceMemory``.
        3. Returns structured feedback to help the caller drive the UI.

        Parameters
        ----------
        frame:
            BGR camera frame.
        timestamp:
            Capture time in Unix seconds.

        Returns
        -------
        EnrollmentFeedback
        """
        if not self._started:
            return EnrollmentFeedback(
                accepted_frame=False,
                reason="Enrollment not started. Call start_enrollment() first.",
                suggested_next_action="call start_enrollment",
                progress_count=0,
                target_count=self.TARGET_CROPS,
            )

        self._frame_index += 1
        current_count = self._memory.count_references()

        # --- locate object via remote grounding ---
        bbox = self._get_object_bbox(frame, self._label)

        if bbox is None:
            action = self._compute_guidance(current_count)
            return EnrollmentFeedback(
                accepted_frame=False,
                reason="Object not detected in frame.",
                suggested_next_action=action,
                progress_count=current_count,
                target_count=self.TARGET_CROPS,
            )

        # --- try to store crop ---
        view_hint = self._compute_guidance(current_count)
        ref = self._memory.add_reference(frame, bbox, timestamp, view_hint=view_hint)

        if ref is None:
            # Could be a duplicate or the store is full
            reason = (
                "Duplicate frame – move to a different angle."
                if current_count < self._memory.MAX_REFS
                else "Reference store is full."
            )
            action = self._compute_guidance(current_count)
            return EnrollmentFeedback(
                accepted_frame=False,
                reason=reason,
                suggested_next_action=action,
                progress_count=current_count,
                target_count=self.TARGET_CROPS,
            )

        self._accepted += 1
        new_count = self._memory.count_references()
        action = self._compute_guidance(new_count)

        return EnrollmentFeedback(
            accepted_frame=True,
            reason="Frame accepted.",
            suggested_next_action=action,
            progress_count=new_count,
            target_count=self.TARGET_CROPS,
        )

    def is_enrollment_complete(self) -> bool:
        """Return *True* once the minimum crop count has been reached."""
        return self._memory.count_references() >= self.MIN_CROPS

    def get_enrollment_progress(self) -> dict:
        """Return a dictionary summarising enrollment progress."""
        return {
            "label": self._label,
            "accepted": self._memory.count_references(),
            "target": self.TARGET_CROPS,
            "min_required": self.MIN_CROPS,
            "frames_analysed": self._frame_index,
            "complete": self.is_enrollment_complete(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_object_bbox(
        self, frame: np.ndarray, label: str
    ) -> list[int] | None:
        """Use remote grounding to get the object bbox in *frame*."""
        result = self._grounding.ground_object(frame, label)
        if result is None:
            return None
        return result.bbox

    def _compute_guidance(self, progress_count: int) -> str:
        """Return the next guidance hint based on how many crops we have."""
        idx = progress_count % len(self._GUIDANCE_ROTATION)
        return self._GUIDANCE_ROTATION[idx]
