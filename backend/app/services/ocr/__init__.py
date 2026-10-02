"""OCR service package."""

from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.paddle_provider import PaddleOCRProvider
from app.services.ocr.tesseract_provider import TesseractOCRProvider
from app.services.ocr.ocr_service import OCRService, get_ocr_service

__all__ = [
    "BaseOCRProvider",
    "PaddleOCRProvider",
    "TesseractOCRProvider",
    "OCRService",
    "get_ocr_service",
]
