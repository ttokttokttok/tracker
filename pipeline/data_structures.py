"""
pipeline/data_structures.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Shared dataclasses used throughout the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EnrollmentFeedback:
    """Feedback returned after analysing a single enrollment frame."""

    accepted_frame: bool
    reason: str
    suggested_next_action: str
    progress_count: int
    target_count: int


@dataclass
class GroundingResult:
    """Result from the remote grounding service."""

    label: str
    query: str
    bbox: list[int]          # [x, y, w, h]
    confidence: float
    timestamp: float
    provider: str


@dataclass
class Reference:
    """A single enrolled reference crop."""

    id: str
    frame_ts: float
    bbox: list[int]          # [x, y, w, h]
    crop_bytes: bytes
    context_crop_bytes: bytes | None
    view_hint: str


@dataclass
class DetectionResult:
    """Result from the local detector for a single frame."""

    bbox: list[int]          # [x, y, w, h]
    confidence: float
    state: str               # "detected" | "weak" | "lost"
    timestamp: float


@dataclass
class TrackResult:
    """Smoothed tracking result for a single frame."""

    bbox: list[int]          # [x, y, w, h]
    smoothed_bbox: list[int]
    confidence: float
    state: str               # "tracking" | "weak" | "lost"
    timestamp: float


@dataclass
class EnrolledObjectState:
    """Full state snapshot of an enrolled object."""

    label: str
    query: str
    enrollment_state: str    # "pending" | "in_progress" | "complete"
    reference_ids: list[str]
    tracking_state: str
    current_bbox: list[int] | None
    tracking_confidence: float
    last_updated_ts: float
