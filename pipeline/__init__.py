"""
tracker/pipeline
~~~~~~~~~~~~~~~~
All pipeline modules for the 2-step enrolled object detection system.
"""

from .data_structures import (
    EnrollmentFeedback,
    GroundingResult,
    Reference,
    DetectionResult,
    TrackResult,
    EnrolledObjectState,
)
from .frame_ingestion import FrameIngestion
from .enrollment_guide import EnrollmentGuide
from .remote_grounding import RemoteGrounding
from .reference_memory import ReferenceMemory
from .local_detector import LocalDetector
from .tracker import Tracker
from .recovery import Recovery
from .overlay_handoff import OverlayHandoff
from .logger import StructuredLogger, LogEvent

__all__ = [
    # Data structures
    "EnrollmentFeedback",
    "GroundingResult",
    "Reference",
    "DetectionResult",
    "TrackResult",
    "EnrolledObjectState",
    # Pipeline modules
    "FrameIngestion",
    "EnrollmentGuide",
    "RemoteGrounding",
    "ReferenceMemory",
    "LocalDetector",
    "Tracker",
    "Recovery",
    "OverlayHandoff",
    "StructuredLogger",
    "LogEvent",
]
