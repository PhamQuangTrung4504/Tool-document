"""Core module containing logging, exceptions, and foundational utilities."""

from app.core.exceptions import (
    ConversionError,
    DocumentError,
    InvalidDocumentError,
    OCRProcessingError,
    UnsupportedFormatError,
)

__all__ = [
    "DocumentError",
    "UnsupportedFormatError",
    "InvalidDocumentError",
    "OCRProcessingError",
    "ConversionError",
]
