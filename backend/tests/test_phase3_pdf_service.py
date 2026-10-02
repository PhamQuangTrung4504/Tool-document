"""Unit tests for Phase 3: PDF Service, Analysis, and Manipulation."""

from pathlib import Path
import numpy as np
import pymupdf
import pytest

from app.models.elements import TextElement
from app.models.geometry import BoundingBox
from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.ocr_service import OCRService
from app.services.pdf.analyzer import PDFType, analyze_pdf
from app.services.pdf.pdf_service import PDFService, get_system_font_path


class DummyOCRForPDF(BaseOCRProvider):
    @property
    def name(self) -> str:
        return "DummyOCRForPDF"

    def is_available(self) -> bool:
        return True

    def recognize(self, image: np.ndarray, lang=None, confidence_threshold=0.5):
        return [
            TextElement(
                text="VĂN BẢN QUY PHẠM PHÁP LUẬT",
                bbox=BoundingBox(x1=50, y1=50, x2=350, y2=80),
                confidence=0.98,
                font_size=14.0,
            ),
            TextElement(
                text="Điều 1. Phạm vi điều chỉnh",
                bbox=BoundingBox(x1=50, y1=100, x2=300, y2=125),
                confidence=0.95,
                font_size=12.0,
            ),
        ]


@pytest.fixture
def sample_text_pdf(tmp_path) -> Path:
    """Generates a native 2-page text PDF with system font for Unicode support."""
    pdf_path = tmp_path / "sample_text.pdf"
    doc = pymupdf.open()
    font_path = get_system_font_path()
    font_kwargs = {"fontfile": font_path, "fontname": "arial"} if font_path else {}

    # Page 1
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text((50, 72), "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", fontsize=14, **font_kwargs)
    page1.insert_text((50, 120), "Nội dung văn bản thử nghiệm trang 1.", fontsize=11, **font_kwargs)

    # Page 2
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((50, 72), "Nội dung văn bản thử nghiệm trang 2.", fontsize=11, **font_kwargs)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_scanned_pdf(tmp_path) -> Path:
    """Generates a scanned-like PDF containing only an image without text layer."""
    pdf_path = tmp_path / "sample_scanned.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=500, height=700)

    # Insert a synthetic image
    pix = pymupdf.Pixmap(pymupdf.csRGB, (0, 0, 400, 600), 1)
    pix.clear_with(240)  # Off-white
    page.insert_image(pymupdf.Rect(50, 50, 450, 650), pixmap=pix)

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_pdf_analyzer(sample_text_pdf, sample_scanned_pdf):
    """Validates classification of text-based vs scanned PDF documents."""
    text_analysis = analyze_pdf(sample_text_pdf)
    assert text_analysis.pdf_type == PDFType.TEXT_BASED
    assert text_analysis.total_pages == 2

    scanned_analysis = analyze_pdf(sample_scanned_pdf)
    assert scanned_analysis.pdf_type == PDFType.SCANNED
    assert scanned_analysis.total_pages == 1


def test_pdf_parse_to_document_model(sample_text_pdf):
    """Validates parsing a native PDF into Document Model."""
    service = PDFService()
    doc = service.parse_to_document(sample_text_pdf)

    assert doc.total_pages == 2
    assert doc.metadata.source_format == "pdf"

    page1 = doc.get_page(1)
    assert page1 is not None
    assert page1.width == 595.0
    assert page1.height == 842.0

    full_text = doc.get_full_text().replace("\xa0", " ")
    assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in full_text
    assert "Nội dung văn bản thử nghiệm trang 2." in full_text


def test_pdf_render_page_to_image(sample_text_pdf):
    """Validates rendering PDF page to numpy image array."""
    service = PDFService()
    img = service.render_page_to_image(sample_text_pdf, page_number=1, dpi=150)

    assert isinstance(img, np.ndarray)
    assert len(img.shape) == 3
    assert img.shape[2] == 3
    assert img.shape[0] > 0 and img.shape[1] > 0


def test_pdf_merge(tmp_path, sample_text_pdf):
    """Validates merging multiple PDFs into one."""
    service = PDFService()
    out_pdf = tmp_path / "merged.pdf"

    merged_path = service.merge_pdfs([sample_text_pdf, sample_text_pdf], out_pdf)
    assert merged_path.exists()

    with pymupdf.open(str(merged_path)) as mdoc:
        assert len(mdoc) == 4  # 2 pages + 2 pages


def test_pdf_split(tmp_path, sample_text_pdf):
    """Validates splitting PDF into individual pages and range expressions."""
    service = PDFService()
    split_dir = tmp_path / "splits"

    # Split all
    files_all = service.split_pdf(sample_text_pdf, split_dir, page_ranges="all")
    assert len(files_all) == 2
    assert files_all[0].exists()

    # Split by range "1-1"
    files_range = service.split_pdf(sample_text_pdf, split_dir, page_ranges="1-1")
    assert len(files_range) == 1
    with pymupdf.open(str(files_range[0])) as rdoc:
        assert len(rdoc) == 1


def test_pdf_rotate_and_extract(tmp_path, sample_text_pdf):
    """Validates rotating pages and extracting specific page subset."""
    service = PDFService()

    # Rotate
    rot_pdf = tmp_path / "rotated.pdf"
    service.rotate_pages(sample_text_pdf, rot_pdf, degrees=90, page_numbers=[1])
    with pymupdf.open(str(rot_pdf)) as rdoc:
        assert rdoc[0].rotation == 90
        assert rdoc[1].rotation == 0

    # Extract
    ext_pdf = tmp_path / "extracted.pdf"
    service.extract_pages(sample_text_pdf, ext_pdf, pages=[2])
    with pymupdf.open(str(ext_pdf)) as edoc:
        assert len(edoc) == 1
        assert "trang 2" in edoc[0].get_text().replace("\xa0", " ")


def test_scanned_pdf_ocr_and_searchable_pdf(tmp_path, sample_scanned_pdf):
    """Validates OCR pipeline on scanned PDF and creation of searchable PDF."""
    dummy_ocr = DummyOCRForPDF()
    ocr_service = OCRService(provider=dummy_ocr)
    pdf_service = PDFService(ocr_service=ocr_service)

    # 1. Parse scanned PDF into Document Model (auto OCR)
    doc_model = pdf_service.parse_to_document(sample_scanned_pdf)
    assert doc_model.total_pages == 1
    page1_text = doc_model.pages[0].get_text().replace("\xa0", " ")
    assert "VĂN BẢN QUY PHẠM PHÁP LUẬT" in page1_text

    # 2. Create searchable PDF
    searchable_pdf = tmp_path / "searchable.pdf"
    pdf_service.create_searchable_pdf(sample_scanned_pdf, searchable_pdf)
    assert searchable_pdf.exists()

    with pymupdf.open(str(searchable_pdf)) as sdoc:
        extracted_text = sdoc[0].get_text().replace("\xa0", " ")
        assert "VĂN BẢN QUY PHẠM PHÁP LUẬT" in extracted_text

