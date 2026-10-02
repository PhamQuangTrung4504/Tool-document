"""Standard enumerations for Document Assistant."""

from enum import Enum


class OCRMode(str, Enum):
    """OCR execution modes balancing throughput vs comprehensive layout correction."""
    FAST = "fast"
    FULL = "full"
    AUTO = "auto"


class JobStatus(str, Enum):
    """Lifecycle status of an asynchronous processing job."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
