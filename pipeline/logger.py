"""
pipeline/logger.py
~~~~~~~~~~~~~~~~~~
Structured JSON-lines logger for the pipeline.

Each log entry is a single-line JSON object written to a log file, making
the log trivially parseable by tools like ``jq``.
"""

from __future__ import annotations

import json
import time
from enum import Enum
from pathlib import Path
from typing import Optional


class LogEvent(str, Enum):
    """Enumeration of all structured log events emitted by the pipeline."""

    ENROLLMENT_STARTED = "enrollment_started"
    ENROLLMENT_FRAME_ACCEPTED = "enrollment_frame_accepted"
    ENROLLMENT_FRAME_REJECTED = "enrollment_frame_rejected"
    ENROLLMENT_COMPLETED = "enrollment_completed"
    INITIAL_GROUNDING = "initial_grounding"
    REFERENCE_ADDED = "reference_added"
    LOCAL_DETECTION_STARTED = "local_detection_started"
    DETECTION_UPDATE = "detection_update"
    TRACKING_STARTED = "tracking_started"
    TRACKING_WEAKENED = "tracking_weakened"
    RECOVERY_ATTEMPT = "recovery_attempt"
    RECOVERY_SUCCESS = "recovery_success"
    RECOVERY_FAILED = "recovery_failed"
    TRACKING_LOST = "tracking_lost"


class StructuredLogger:
    """Writes structured JSON-line log entries to a file and memory.

    Each entry has the shape::

        {
            "session_id": "...",
            "ts": 1700000000.123,
            "event": "detection_update",
            "object": "cup",
            ...extra fields...
        }
    """

    def __init__(self, session_id: str, log_file: str = "session.log") -> None:
        self._session_id = session_id
        self._log_file = Path(log_file)
        self._events: list[dict] = []

        # Ensure the log file is writable (create or truncate)
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        # Open in append mode so that multiple sessions can coexist in one file
        self._fh = self._log_file.open("a", encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log(
        self,
        event: LogEvent,
        object_label: str = "",
        extra: Optional[dict] = None,
    ) -> None:
        """Emit a structured log entry.

        Parameters
        ----------
        event:
            One of the ``LogEvent`` enum values.
        object_label:
            The enrolled object this event relates to (may be empty).
        extra:
            Arbitrary additional fields to include in the entry.
        """
        entry: dict = {
            "session_id": self._session_id,
            "ts": time.time(),
            "event": event.value,
            "object": object_label,
        }
        if extra:
            entry.update(extra)

        self._events.append(entry)
        self._fh.write(json.dumps(entry) + "\n")
        self._fh.flush()

    def get_events(self) -> list[dict]:
        """Return all log entries recorded during this session."""
        return list(self._events)

    def close(self) -> None:
        """Flush and close the underlying log file."""
        self._fh.flush()
        self._fh.close()

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "StructuredLogger":
        return self

    def __exit__(self, *_) -> None:
        self.close()
