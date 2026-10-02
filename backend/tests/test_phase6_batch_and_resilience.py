"""Unit tests for Phase 6: Batch Processing, Resilience, and Error Isolation."""

from pathlib import Path
import pymupdf
import pytest

from app.core.exceptions import (
    ConversionError,
    DocumentError,
    InvalidDocumentError,
    OCRProcessingError,
    UnsupportedFormatError,
)
from app.services.batch.batch_processor import BatchProcessor
from app.services.converter.converter_service import ConversionService
from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.ocr_service import OCRService


class SimpleOCRProvider(BaseOCRProvider):
    @property
    def name(self) -> str:
        return "SimpleOCR"

    def is_available(self) -> bool:
        return True

    def recognize(self, image, lang=None, confidence_threshold=0.5):
        return []


def test_batch_processor_success_and_resilience(tmp_path):
    """Validates batch processing with mixed valid and invalid files."""
    # 1. Create 2 valid text PDF files
    valid_pdf1 = tmp_path / "doc1.pdf"
    doc1 = pymupdf.open()
    p1 = doc1.new_page(width=400, height=400)
    p1.insert_text((50, 50), "Document 1 content")
    doc1.save(str(valid_pdf1))
    doc1.close()

    valid_pdf2 = tmp_path / "doc2.pdf"
    doc2 = pymupdf.open()
    p2 = doc2.new_page(width=400, height=400)
    p2.insert_text((50, 50), "Document 2 content")
    doc2.save(str(valid_pdf2))
    doc2.close()

    # 3rd file does not exist
    invalid_file = tmp_path / "non_existent.pdf"

    files = [valid_pdf1, invalid_file, valid_pdf2]
    progress_records = []

    def on_progress(current, total, file_p):
        progress_records.append((current, total, file_p.name))

    conv = ConversionService(ocr_service=OCRService(provider=SimpleOCRProvider()))
    processor = BatchProcessor(converter=conv)

    out_dir = tmp_path / "batch_out"
    report = processor.convert_all(files, to_format="txt", output_dir=out_dir, progress_callback=on_progress)

    # Validations
    assert report.total == 3
    assert report.succeeded == 2
    assert report.failed == 1
    assert pytest.approx(report.success_rate, 0.1) == 66.66

    assert len(progress_records) == 3
    assert progress_records[0] == (1, 3, "doc1.pdf")
    assert progress_records[1] == (2, 3, "non_existent.pdf")
    assert progress_records[2] == (3, 3, "doc2.pdf")

    # Output files check
    assert (out_dir / "doc1.txt").exists()
    assert (out_dir / "doc2.txt").exists()

    # Check failure record
    failed_items = [r for r in report.results if r.status == "failed"]
    assert len(failed_items) == 1
    assert "non_existent.pdf" in str(failed_items[0].file_path)
    assert failed_items[0].error_message is not None


def test_exception_hierarchy():
    """Validates exception hierarchy and details dictionary."""
    exc1 = UnsupportedFormatError("xyz")
    assert isinstance(exc1, DocumentError)
    assert exc1.details == {"format": "xyz"}

    exc2 = InvalidDocumentError("file.pdf", "Corrupt EOF")
    assert isinstance(exc2, DocumentError)
    assert exc2.details["reason"] == "Corrupt EOF"

    exc3 = ConversionError("pdf", "xyz", "Target not supported")
    assert isinstance(exc3, DocumentError)
    assert exc3.details["target_format"] == "xyz"

    exc4 = OCRProcessingError("Timeout", provider="PaddleOCR")
    assert isinstance(exc4, DocumentError)
    assert exc4.details["provider"] == "PaddleOCR"
