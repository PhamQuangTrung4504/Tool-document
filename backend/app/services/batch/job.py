"""Job abstraction and cancellation token system for asynchronous task execution."""

import threading
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.cancellation import CancellationToken, OperationCancelledError
from app.models.enums import JobStatus


class Job(BaseModel):
    """Encapsulates a unit of background work with progress reporting and cancellation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    operation: str = Field(..., description="Action name (e.g. 'convert', 'ocr', 'merge')")
    status: JobStatus = Field(default=JobStatus.QUEUED)
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage completed [0.0 - 100.0]")
    message: str = Field(default="Queued", description="Current stage description")
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    # Exclude token from pydantic serialization
    _token: CancellationToken = None

    def model_post_init(self, __context: Any) -> None:
        self._token = CancellationToken()

    @property
    def token(self) -> CancellationToken:
        if self._token is None:
            self._token = CancellationToken()
        return self._token

    def update_progress(self, progress: float, message: Optional[str] = None) -> None:
        """Updates job progress and current status message."""
        self.progress = max(0.0, min(100.0, progress))
        if message:
            self.message = message
        if self.status == JobStatus.QUEUED and self.progress > 0:
            self.status = JobStatus.RUNNING

    def complete(self, result: Optional[Dict[str, Any]] = None, message: str = "Completed successfully") -> None:
        """Marks the job as successfully completed."""
        self.status = JobStatus.COMPLETED
        self.progress = 100.0
        self.message = message
        self.result = result or {}

    def fail(self, code: str, message: str) -> None:
        """Marks the job as failed with standardized error code and safe message."""
        self.status = JobStatus.FAILED
        self.message = message
        self.error = {"code": code, "message": message}

    def cancel(self) -> None:
        """Requests cooperative cancellation of the job."""
        self.token.cancel()
        self.status = JobStatus.CANCELLED
        self.message = "Cancelled by user"


class JobManager:
    """Thread-safe registry managing background job lifecycles."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create_job(self, operation: str, job_id: Optional[str] = None) -> Job:
        """Registers a new job in the registry."""
        with self._lock:
            jid = job_id or str(uuid.uuid4())
            job = Job(id=jid, operation=operation)
            self._jobs[jid] = job
            return job

    def get_job(self, job_id: str) -> Optional[Job]:
        """Retrieves a job by its unique identifier."""
        with self._lock:
            return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """Cancels a running or queued job."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                job.cancel()
                return True
            return False

    def list_jobs(self) -> List[Job]:
        """Returns all registered jobs."""
        with self._lock:
            return list(self._jobs.values())


# Global singleton instance
job_manager = JobManager()
