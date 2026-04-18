"""
orchestrator.py
~~~~~~~~~~~~~~~
Top-level pipeline orchestrator tying together all modules.

Two-step flow
-------------
Step 1 – Enrollment
    begin_enrollment(label)
        → process_enrollment_frame(frame)  [repeat until complete]
        → finish_enrollment()

Step 2 – Tracking
    process_tracking_frame(frame)  [repeat each camera frame]

State can be inspected at any time via get_state().
reset() returns the pipeline to the pre-enrollment state.
"""

from __future__ import annotations

import tempfile
import time
import uuid
from typing import Optional

import numpy as np

from pipeline.data_structures import (
    EnrolledObjectState,
    EnrollmentFeedback,
    TrackResult,
)
from pipeline.enrollment_guide import EnrollmentGuide
from pipeline.frame_ingestion import FrameIngestion
from pipeline.local_detector import LocalDetector
from pipeline.logger import LogEvent, StructuredLogger
from pipeline.overlay_handoff import OverlayHandoff
from pipeline.recovery import Recovery
from pipeline.reference_memory import ReferenceMemory
from pipeline.remote_grounding import RemoteGrounding
from pipeline.yolo_grounding import YOLOGrounding
from pipeline.tracker import Tracker


class Pipeline:
    """Orchestrates the full 2-step enrollment + detection pipeline.

    Parameters
    ----------
    session_id:
        Unique identifier for this pipeline session.  Auto-generated when
        *None*.
    storage_dir:
        Directory to use for reference crop storage.  A temporary directory
        is created automatically when *None*.
    log_file:
        Path for the JSON-lines session log.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        storage_dir: Optional[str] = None,
        log_file: str = "session.log",
    ) -> None:
        self._session_id = session_id or str(uuid.uuid4())[:8]

        # Storage directory for reference crops
        if storage_dir is None:
            self._tmp_dir = tempfile.mkdtemp(prefix="tracker_refs_")
            storage_dir = self._tmp_dir
        else:
            self._tmp_dir = None

        # Instantiate all sub-modules
        self._ingestion = FrameIngestion(max_buffer=60)
        try:
            self._remote_grounding = YOLOGrounding()
        except Exception:
            self._remote_grounding = RemoteGrounding(provider="mock")
        self._reference_memory = ReferenceMemory(storage_dir=storage_dir)
        self._enrollment_guide = EnrollmentGuide(
            reference_memory=self._reference_memory,
            remote_grounding=self._remote_grounding,
        )
        self._local_detector = LocalDetector()
        self._tracker = Tracker()
        self._recovery = Recovery(remote_grounding=self._remote_grounding)
        self._overlay_handoff = OverlayHandoff()
        self._logger = StructuredLogger(
            session_id=self._session_id, log_file=log_file
        )

        # Internal state
        self._label: str = ""
        self._query: str = ""
        self._enrollment_state: str = "pending"   # pending | in_progress | complete
        self._track_history: list[TrackResult] = []
        self._last_track: Optional[TrackResult] = None

    # ------------------------------------------------------------------
    # Step 1: Enrollment
    # ------------------------------------------------------------------

    def begin_enrollment(self, object_label: str) -> None:
        """Begin enrollment for *object_label*.

        Resets any previously enrolled state and starts a fresh enrollment
        session.
        """
        self._label = object_label
        self._query = object_label
        self._enrollment_state = "in_progress"
        self._reference_memory.clear()
        self._local_detector.reset()
        self._tracker.reset()
        self._track_history.clear()
        self._last_track = None

        self._enrollment_guide.start_enrollment(object_label)
        self._logger.log(
            LogEvent.ENROLLMENT_STARTED,
            object_label=object_label,
            extra={"session_id": self._session_id},
        )

    def process_enrollment_frame(self, frame: np.ndarray) -> EnrollmentFeedback:
        """Feed a single camera frame to the enrollment guide.

        The guide calls the remote grounding service internally and updates
        the reference memory if the frame is accepted.

        Parameters
        ----------
        frame:
            BGR camera frame.

        Returns
        -------
        EnrollmentFeedback
        """
        ts = self._ingestion.ingest(frame)
        feedback = self._enrollment_guide.analyze_enrollment_frame(frame, ts)

        if feedback.accepted_frame:
            self._logger.log(
                LogEvent.ENROLLMENT_FRAME_ACCEPTED,
                object_label=self._label,
                extra={
                    "progress": feedback.progress_count,
                    "hint": feedback.suggested_next_action,
                },
            )
            self._logger.log(
                LogEvent.REFERENCE_ADDED,
                object_label=self._label,
                extra={"progress": feedback.progress_count},
            )
        else:
            self._logger.log(
                LogEvent.ENROLLMENT_FRAME_REJECTED,
                object_label=self._label,
                extra={"reason": feedback.reason},
            )

        return feedback

    def finish_enrollment(self) -> EnrolledObjectState:
        """Finalise enrollment and initialise the local detector.

        Raises
        ------
        RuntimeError
            If the minimum reference count has not been reached.

        Returns
        -------
        EnrolledObjectState
            A snapshot of the pipeline state after enrollment.
        """
        if not self._enrollment_guide.is_enrollment_complete():
            raise RuntimeError(
                f"Enrollment is not complete yet. "
                f"Need at least {self._enrollment_guide.MIN_CROPS} references; "
                f"have {self._reference_memory.count_references()}."
            )

        # Initialise local detector — pass YOLO instance for per-frame inference
        ref_set = self._reference_memory.build_reference_set()
        self._local_detector.initialize(
            ref_set,
            grounding=self._remote_grounding,
            query=self._query,
        )
        self._enrollment_state = "complete"

        self._logger.log(
            LogEvent.ENROLLMENT_COMPLETED,
            object_label=self._label,
            extra={"reference_count": len(ref_set)},
        )
        self._logger.log(
            LogEvent.LOCAL_DETECTION_STARTED,
            object_label=self._label,
        )

        return self.get_state()

    # ------------------------------------------------------------------
    # Step 2: Detection / Tracking
    # ------------------------------------------------------------------

    def process_tracking_frame(self, frame: np.ndarray) -> TrackResult:
        """Process a single frame during the tracking phase.

        Pipeline flow
        -------------
        1. Ingest frame into the frame buffer.
        2. Run ``local_detector.detect()``.
        3. Run ``tracker.update()``.
        4. Check ``recovery.should_recover()``.
           - If yes: call ``recovery.recover()``, re-seed tracker with new bbox.
        5. Call ``overlay_handoff.emit_bbox()``.
        6. Log a DETECTION_UPDATE event.
        7. Return the ``TrackResult``.

        Parameters
        ----------
        frame:
            BGR camera frame.

        Returns
        -------
        TrackResult
        """
        if self._enrollment_state != "complete":
            raise RuntimeError(
                "Cannot track before enrollment is complete. "
                "Call finish_enrollment() first."
            )

        # 1. Ingest
        self._ingestion.ingest(frame)

        # 2. Local detection
        detection = self._local_detector.detect(frame)

        # 3. Track (EMA smooth)
        track_result = self._tracker.update(detection)

        # 4. Recovery check
        if self._recovery.should_recover(track_result, self._track_history):
            self._logger.log(
                LogEvent.RECOVERY_ATTEMPT,
                object_label=self._label,
                extra={"confidence": track_result.confidence},
            )
            grounding = self._recovery.recover(frame, self._query)
            if grounding is not None:
                # Re-seed the tracker with the recovered bbox
                self._tracker.start(grounding.bbox)
                # Create a synthetic TrackResult from the grounding
                track_result = TrackResult(
                    bbox=grounding.bbox,
                    smoothed_bbox=grounding.bbox,
                    confidence=grounding.confidence,
                    state="tracking",
                    timestamp=grounding.timestamp,
                )
                self._logger.log(
                    LogEvent.RECOVERY_SUCCESS,
                    object_label=self._label,
                    extra={"bbox": grounding.bbox},
                )
            else:
                self._logger.log(
                    LogEvent.RECOVERY_FAILED,
                    object_label=self._label,
                )

        # Log state transitions
        if self._last_track is not None:
            if (
                self._last_track.state in ("tracking",)
                and track_result.state == "weak"
            ):
                self._logger.log(
                    LogEvent.TRACKING_WEAKENED,
                    object_label=self._label,
                    extra={"confidence": track_result.confidence},
                )
            elif track_result.state == "lost" and (
                self._last_track is None or self._last_track.state != "lost"
            ):
                self._logger.log(
                    LogEvent.TRACKING_LOST,
                    object_label=self._label,
                )
        else:
            # First tracking frame
            self._logger.log(
                LogEvent.TRACKING_STARTED,
                object_label=self._label,
                extra={"bbox": track_result.bbox},
            )

        # 5. Overlay handoff
        self._overlay_handoff.emit_bbox(track_result)

        # 6. Detection update log
        self._logger.log(
            LogEvent.DETECTION_UPDATE,
            object_label=self._label,
            extra={
                "bbox": track_result.bbox,
                "confidence": track_result.confidence,
                "state": track_result.state,
            },
        )

        # Update history
        self._track_history.append(track_result)
        self._last_track = track_result

        # 7. Return
        return track_result

    # ------------------------------------------------------------------
    # State / lifecycle
    # ------------------------------------------------------------------

    def get_state(self) -> EnrolledObjectState:
        """Return a snapshot of the current pipeline state."""
        refs = self._reference_memory.get_references()
        latest = self._overlay_handoff.get_latest_bbox()

        return EnrolledObjectState(
            label=self._label,
            query=self._query,
            enrollment_state=self._enrollment_state,
            reference_ids=[r.id for r in refs],
            tracking_state=latest.state if latest else "pending",
            current_bbox=latest.smoothed_bbox if latest else None,
            tracking_confidence=latest.confidence if latest else 0.0,
            last_updated_ts=latest.timestamp if latest else time.time(),
        )

    def reset(self) -> None:
        """Reset the entire pipeline to its initial pre-enrollment state."""
        self._label = ""
        self._query = ""
        self._enrollment_state = "pending"
        self._reference_memory.clear()
        self._local_detector.reset()
        self._tracker.reset()
        self._track_history.clear()
        self._last_track = None
        self._ingestion.clear()

    # ------------------------------------------------------------------
    # Expose sub-modules (useful for testing / advanced usage)
    # ------------------------------------------------------------------

    @property
    def remote_grounding(self) -> RemoteGrounding:
        return self._remote_grounding

    @property
    def reference_memory(self) -> ReferenceMemory:
        return self._reference_memory

    @property
    def local_detector(self) -> LocalDetector:
        return self._local_detector

    @property
    def tracker(self) -> Tracker:
        return self._tracker

    @property
    def recovery(self) -> Recovery:
        return self._recovery

    @property
    def overlay_handoff(self) -> OverlayHandoff:
        return self._overlay_handoff

    @property
    def logger(self) -> StructuredLogger:
        return self._logger

    @property
    def enrollment_guide(self) -> EnrollmentGuide:
        return self._enrollment_guide
