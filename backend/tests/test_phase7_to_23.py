"""Comprehensive Integration and Unit Tests for Phases 7 - 23.

Covers:
- OCR FAST, FULL, and AUTO modes (Phases 7 & 8)
- Table Structure Recognition & Zero-content-loss Fallback (Phases 9 & 10)
- Enhanced Layout Reconstruction & Two-Column Reading Order (Phases 11 & 12)
- Objective Document Fidelity Metrics (Phase 13)
- Local IPC Contract, Validation, and Secure Error Masking (Phase 14)
- Job Lifecycle Model and Cooperative Cancellation (Phases 15 & 16)
- Secure Temp Workspace and Intermediate File Cleanup (Phase 17)
"""

import json
from pathlib import Path
import time
import numpy as np
import pytest
from PIL import Image

from app.core.cancellation import CancellationToken, OperationCancelledError
from app.core.exceptions import InvalidDocumentError
from app.core.ipc import IPCHandler
from app.models.document import Document, DocumentMetadata, Page
from app.models.elements import BoundingBox, TableCell, TableElement, TextAlignment, TextElement
from app.models.enums import JobStatus, OCRMode
from app.models.fidelity import DocumentFidelityReport
from app.services.batch.job import Job, JobManager, job_manager
from app.services.converter.converter_service import ConversionService
from app.services.docx.docx_service import DOCXService
from app.services.fidelity.fidelity_service import DocumentFidelityService
from app.services.ocr.ocr_service import OCRService
from app.services.ocr.paddle_provider import PaddleOCRProvider
from app.services.pdf.pdf_service import PDFService
from app.services.table.base import TableStructureProvider
from app.services.table.table_service import TableService
from app.utils.workspace import TempWorkspace
from tests.generate_fixtures import create_all_fixtures


@pytest.fixture(scope="module")
def fixtures(tmp_path_factory) -> dict:
    fix_dir = Path("tests/fixtures")
    return create_all_fixtures(fix_dir)


# ==============================================================================
# PHASES 7 & 8: OCR FAST, FULL, AND AUTO MODES
# ==============================================================================

def test_ocr_fast_mode_recognition(fixtures):
    """Phase 7: Verifies OCRMode.FAST executes text detection and recognition."""
    ocr = OCRService()
    elements = ocr.recognize_image(fixtures["scan_clean"], mode=OCRMode.FAST)
    assert len(elements) > 0
    all_text = " ".join(e.text for e in elements)
    assert any(term in all_text for term in ["ỦY BAN", "CỘNG HÒA", "VIỆT NAM", "HÒA"])


def test_ocr_process_alias(fixtures):
    """Phase 7: Verifies ocr_service.process(input, mode=...) standard alias."""
    ocr = OCRService()
    elements = ocr.process(fixtures["scan_clean"], mode=OCRMode.FAST)
    assert len(elements) > 0


def test_ocr_auto_mode_heuristic_selection(fixtures):
    """Phase 8: Verifies AUTO mode heuristically chooses FAST for clean image and FULL for skewed."""
    ocr = OCRService()

    # Clean straight image -> heuristic should choose FAST
    clean_arr = np.array(Image.open(fixtures["scan_clean"]))
    mode_clean = ocr._resolve_auto_mode(clean_arr)
    assert mode_clean == OCRMode.FAST

    # Tilted 5-degree image -> heuristic should detect skew > 2.5° and choose FULL
    tilted_arr = np.array(Image.open(fixtures["scan_tilted"]))
    mode_tilted = ocr._resolve_auto_mode(tilted_arr)
    assert mode_tilted == OCRMode.FULL

    # Calling recognize_image in AUTO mode works end-to-end
    elements = ocr.recognize_image(fixtures["scan_clean"], mode=OCRMode.AUTO)
    assert len(elements) > 0


# ==============================================================================
# PHASES 9 & 10: TABLE STRUCTURE & ZERO-CONTENT-LOSS FALLBACK
# ==============================================================================

class MockFailingTableProvider(TableStructureProvider):
    @property
    def name(self) -> str:
        return "MockFailingProvider"

    def is_available(self) -> bool:
        return True

    def detect_tables(self, image, ocr_elements=None, confidence_threshold=0.5):
        raise RuntimeError("Model engine simulated failure")


class MockSuccessfulTableProvider(TableStructureProvider):
    @property
    def name(self) -> str:
        return "MockSuccessfulProvider"

    def is_available(self) -> bool:
        return True

    def detect_tables(self, image, ocr_elements=None, confidence_threshold=0.5):
        # Builds a sample 2x2 table inside bounds (100, 100) to (300, 200)
        c00 = TableCell(row_index=0, col_index=0, text="Header 1", bbox=BoundingBox(x1=100, y1=100, x2=200, y2=150))
        c01 = TableCell(row_index=0, col_index=1, text="Header 2", bbox=BoundingBox(x1=200, y1=100, x2=300, y2=150))
        c10 = TableCell(row_index=1, col_index=0, text="Data 1", bbox=BoundingBox(x1=100, y1=150, x2=200, y2=200))
        c11 = TableCell(row_index=1, col_index=1, text="Data 2", bbox=BoundingBox(x1=200, y1=150, x2=300, y2=200))

        # Assign elements that fall into cell bounds
        if ocr_elements:
            for c in [c00, c01, c10, c11]:
                matched = [el for el in ocr_elements if c.bbox.contains_point(el.bbox.center_x, el.bbox.center_y)]
                c.elements = matched
                if matched:
                    c.text = " ".join(t.text for t in matched)

        table = TableElement(
            bbox=BoundingBox(x1=100, y1=100, x2=300, y2=200),
            rows=2,
            columns=2,
            cells=[c00, c01, c10, c11],
            confidence=0.95,
        )
        return [table]


def test_table_fallback_zero_content_loss():
    """Phase 10: Ensures when Table Structure Recognition fails, NO OCR text is lost."""
    failing_service = TableService(provider=MockFailingTableProvider())

    sample_texts = [
        TextElement(text="Header Title", bbox=BoundingBox(x1=50, y1=20, x2=250, y2=40)),
        TextElement(text="Item Row 1", bbox=BoundingBox(x1=110, y1=110, x2=190, y2=140)),
        TextElement(text="Value Row 1", bbox=BoundingBox(x1=210, y1=110, x2=290, y2=140)),
        TextElement(text="Footer Notice", bbox=BoundingBox(x1=50, y1=400, x2=300, y2=420)),
    ]

    dummy_img = np.zeros((500, 500, 3), dtype=np.uint8)
    tables, remaining_texts = failing_service.detect_tables(dummy_img, ocr_elements=sample_texts)

    # Tables detection failed gracefully -> returned empty tables list
    assert len(tables) == 0
    # ZERO content lost: exactly 4 elements remain as standalone text
    assert len(remaining_texts) == 4
    assert [t.text for t in remaining_texts] == [t.text for t in sample_texts]


def test_table_structure_absorption_and_outside_text_preservation():
    """Phase 9 & 10: Table absorbs inner text while outer text remains standalone."""
    succ_service = TableService(provider=MockSuccessfulTableProvider())

    inner1 = TextElement(text="H1 Text", bbox=BoundingBox(x1=110, y1=110, x2=190, y2=140))
    inner2 = TextElement(text="D1 Text", bbox=BoundingBox(x1=110, y1=160, x2=190, y2=190))
    outer_title = TextElement(text="Top Document Title", bbox=BoundingBox(x1=50, y1=20, x2=350, y2=45))
    outer_footer = TextElement(text="Bottom Document Note", bbox=BoundingBox(x1=50, y1=450, x2=350, y2=475))

    all_ocr = [outer_title, inner1, inner2, outer_footer]
    dummy_img = np.zeros((500, 500, 3), dtype=np.uint8)

    tables, remaining_texts = succ_service.detect_tables(dummy_img, ocr_elements=all_ocr)

    assert len(tables) == 1
    assert tables[0].rows == 2
    assert tables[0].columns == 2
    assert tables[0].confidence == 0.95

    # 2 inner elements absorbed into table
    # 2 outer elements remain intact
    assert len(remaining_texts) == 2
    assert [t.text for t in remaining_texts] == ["Top Document Title", "Bottom Document Note"]


# ==============================================================================
# PHASES 11 & 12: DOCUMENT RECONSTRUCTION & TWO-COLUMN READING ORDER
# ==============================================================================

def test_two_column_reading_order():
    """Phase 12: Two-column layout must order Column 1 (top-to-bottom) then Column 2 (top-to-bottom)."""
    page = Page(page_number=1, width=600.0, height=800.0)

    # Full width header banner
    title = TextElement(text="FULL WIDTH BANNER", bbox=BoundingBox(x1=50, y1=30, x2=550, y2=50), is_header=True)

    # Left column (Column A): X in [50..250], Y in [100, 150, 200]
    a1 = TextElement(text="Column A1", bbox=BoundingBox(x1=50, y1=100, x2=200, y2=120))
    a2 = TextElement(text="Column A2", bbox=BoundingBox(x1=50, y1=150, x2=200, y2=170))
    a3 = TextElement(text="Column A3", bbox=BoundingBox(x1=50, y1=200, x2=200, y2=220))

    # Right column (Column B): X in [350..550], Y in [100, 150, 200]
    b1 = TextElement(text="Column B1", bbox=BoundingBox(x1=350, y1=100, x2=500, y2=120))
    b2 = TextElement(text="Column B2", bbox=BoundingBox(x1=350, y1=150, x2=500, y2=170))
    b3 = TextElement(text="Column B3", bbox=BoundingBox(x1=350, y1=200, x2=500, y2=220))

    # Footer
    footer = TextElement(text="PAGE FOOTER", bbox=BoundingBox(x1=50, y1=760, x2=300, y2=780), is_footer=True)

    # Add elements in arbitrary unordered order
    page.elements = [b2, a1, footer, b1, a3, title, b3, a2]

    sorted_elements = page.get_sorted_elements()
    ordered_texts = [e.text for e in sorted_elements if isinstance(e, TextElement)]

    # Expected order: Title -> A1 -> A2 -> A3 -> B1 -> B2 -> B3 -> Footer
    expected = ["FULL WIDTH BANNER", "Column A1", "Column A2", "Column A3", "Column B1", "Column B2", "Column B3", "PAGE FOOTER"]
    assert ordered_texts == expected


# ==============================================================================
# PHASE 13: DOCUMENT FIDELITY METRICS
# ==============================================================================

def test_document_fidelity_metrics_computation(fixtures):
    """Phase 13: Evaluates objective fidelity metrics between Document models."""
    pdf_service = PDFService()
    doc_model = pdf_service.parse_to_document(fixtures["admin_pdf"])

    report = DocumentFidelityService.evaluate(doc_model)

    assert isinstance(report, DocumentFidelityReport)
    assert report.source_pages == 2
    assert report.output_pages == 2
    assert report.source_text_chars > 0
    assert report.text_coverage == 1.0
    assert report.ocr_confidence_avg > 0.90
    assert report.element_count > 0
    assert report.bounding_box_coverage > 0.0
    assert isinstance(report.warnings, list)


# ==============================================================================
# PHASE 14: STANDARDIZED IPC CONTRACT & ERROR MASKING
# ==============================================================================

def test_ipc_handler_info_and_convert(tmp_path, fixtures):
    """Phase 14: Tests IPC request dispatching and response contract formatting."""
    ipc = IPCHandler()

    # 1. Info Request
    info_req = {
        "operation": "info",
        "input": str(fixtures["admin_pdf"]),
    }
    info_resp = ipc.handle(info_req)
    assert info_resp["success"] is True
    assert info_resp["operation"] == "info"
    assert info_resp["output"]["total_pages"] == 2
    assert "processing_time_ms" in info_resp["metrics"]

    # 2. Convert Request
    out_docx = tmp_path / "ipc_converted.docx"
    convert_req = {
        "operation": "convert",
        "input": str(fixtures["admin_pdf"]),
        "output": str(out_docx),
        "options": {
            "to_format": "docx",
            "ocr_mode": "fast",
        },
    }
    convert_resp = ipc.handle(convert_req)
    assert convert_resp["success"] is True
    assert convert_resp["operation"] == "convert"
    assert Path(convert_resp["output"]).exists()
    assert convert_resp["metrics"]["ocr_mode"] == "fast"


def test_ipc_handler_error_masking():
    """Phase 14: Verifies malformed inputs or missing files return clean errors without stack traces."""
    ipc = IPCHandler()

    # Malformed JSON string
    resp1 = ipc.handle("{invalid_json:")
    assert resp1["success"] is False
    assert resp1["error"]["code"] == "INVALID_JSON"

    # Missing operation
    resp2 = ipc.handle({"input": "some_file.pdf"})
    assert resp2["success"] is False
    assert resp2["error"]["code"] == "MISSING_OPERATION"

    # Non-existent file
    resp3 = ipc.handle({"operation": "convert", "input": "Z:/NonExistentPath/random.pdf"})
    assert resp3["success"] is False
    assert resp3["error"]["code"] in ("INVALID_DOCUMENT_ERROR", "FILE_NOT_FOUND")
    # Verify no raw trace exposed
    assert "Traceback" not in resp3["error"]["message"]


# ==============================================================================
# PHASES 15 & 16: JOB MODEL & COOPERATIVE CANCELLATION
# ==============================================================================

def test_job_model_lifecycle():
    """Phase 15: Tests job creation, progress tracking, and completion."""
    mgr = JobManager()
    job = mgr.create_job("convert")

    assert job.status == JobStatus.QUEUED
    assert job.progress == 0.0

    job.update_progress(50.0, "Processing page 1/2")
    assert job.status == JobStatus.RUNNING
    assert job.progress == 50.0
    assert job.message == "Processing page 1/2"

    job.complete({"output": "result.docx"})
    assert job.status == JobStatus.COMPLETED
    assert job.progress == 100.0
    assert job.result == {"output": "result.docx"}


def test_cancellation_token_mechanism(fixtures):
    """Phase 16: Tests cancellation token interrupts multi-page PDF parsing gracefully."""
    token = CancellationToken()
    assert not token.is_cancelled

    token.cancel()
    assert token.is_cancelled

    with pytest.raises(OperationCancelledError):
        token.check_cancelled()

    # Test PDF parsing aborts on cancelled token
    pdf_service = PDFService()
    with pytest.raises(OperationCancelledError):
        pdf_service.parse_to_document(fixtures["admin_pdf"], cancellation_token=token)


# ==============================================================================
# PHASE 17: TEMP FILE MANAGEMENT & CLEANUP
# ==============================================================================

def test_temp_workspace_cleanup(tmp_path):
    """Phase 17: Verifies intermediate directory is safely created and automatically cleaned."""
    job_id = "test-job-audit-17"

    with TempWorkspace(job_id=job_id, base_dir=tmp_path) as ws:
        assert ws.input_dir.exists()
        assert ws.intermediate_dir.exists()
        assert ws.output_dir.exists()

        # Create a mock intermediate file (rendered page image)
        inter_file = ws.intermediate_dir / "page_1.png"
        inter_file.write_bytes(b"dummy pixel data")
        assert inter_file.exists()

    # After exit from context manager, intermediate_dir is cleaned up
    assert not (ws.intermediate_dir / "page_1.png").exists()

    # Clean entire workspace
    ws.cleanup_all()
    assert not ws.root_dir.exists()
