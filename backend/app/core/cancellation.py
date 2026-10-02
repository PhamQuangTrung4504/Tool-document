import threading
from app.core.exceptions import DocumentError


class OperationCancelledError(DocumentError):
    """Raised when an ongoing document conversion or OCR task is cancelled gracefully."""

    def __init__(self, message: str = "Operation was cancelled by user") -> None:
        super().__init__(message)


class CancellationToken:
    """Thread-safe cooperative cancellation token checked between processing stages and pages."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        """Triggers cancellation request."""
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Returns True if cancellation has been requested."""
        return self._event.is_set()

    def check_cancelled(self) -> None:
        """Raises OperationCancelledError if cancellation has been requested."""
        if self.is_cancelled:
            raise OperationCancelledError()
