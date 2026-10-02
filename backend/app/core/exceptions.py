"""Core exceptions for Document Assistant Backend.

Provides a structured exception hierarchy ensuring consistent error handling
and clear, user-friendly messages across all modules.
"""

from typing import Optional, Any


class DocumentError(Exception):
    """Base exception class for all Document Assistant errors."""

    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


DocumentAssistantError = DocumentError


class UnsupportedFormatError(DocumentError):
    """Raised when an unsupported file format or extension is encountered."""

    def __init__(self, format_name: str, message: Optional[str] = None) -> None:
        msg = message or f"Unsupported file format: '{format_name}'."
        super().__init__(msg, details={"format": format_name})


class InvalidDocumentError(DocumentError):
    """Raised when a document file is corrupted, malformed, or cannot be parsed."""

    def __init__(self, path_or_info: str, reason: str) -> None:
        msg = f"Invalid or corrupted document '{path_or_info}': {reason}"
        super().__init__(msg, details={"target": path_or_info, "reason": reason})


class OCRProcessingError(DocumentError):
    """Raised when an OCR operation fails or encounters an unrecoverable engine error."""

    def __init__(self, reason: str, provider: Optional[str] = None) -> None:
        provider_str = f" [{provider}]" if provider else ""
        msg = f"OCR processing failed{provider_str}: {reason}"
        super().__init__(msg, details={"provider": provider, "reason": reason})


class ConversionError(DocumentError):
    """Raised when conversion between document formats fails."""

    def __init__(self, source_format: str, target_format: str, reason: str) -> None:
        msg = f"Failed to convert from '{source_format}' to '{target_format}': {reason}"
        super().__init__(
            msg,
            details={
                "source_format": source_format,
                "target_format": target_format,
                "reason": reason,
            },
        )
