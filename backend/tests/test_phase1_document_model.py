"""Unit tests for Phase 1: Document Model, Geometry, and File Detection."""

import io
import zipfile
import pytest

from app.core.exceptions import (
    DocumentError,
    UnsupportedFormatError,
    InvalidDocumentError,
    OCRProcessingError,
    ConversionError,
)
from app.models.geometry import BoundingBox
from app.models.elements import (
    TextElement,
    ImageElement,
    TableCell,
    TableElement,
    ShapeElement,
    TextAlignment,
    ShapeType,
)
from app.models.document import (
    Document,
    DocumentMetadata,
    DocumentStyle,
    Page,
)
from app.utils.file_type import FileType, detect_file_type
from app.config import config


def test_bounding_box_basics():
    """Validates geometry coordinates, width, height, area, and normalization."""
    bbox = BoundingBox(x1=10.0, y1=20.0, x2=50.0, y2=80.0)
    assert bbox.width == 40.0
    assert bbox.height == 60.0
    assert bbox.area == 2400.0
    assert bbox.center == (30.0, 50.0)

    # Inverted coordinates auto-correction
    inverted = BoundingBox(x1=50.0, y1=80.0, x2=10.0, y2=20.0)
    assert inverted.x1 == 10.0
    assert inverted.x2 == 50.0
    assert inverted.y1 == 20.0
    assert inverted.y2 == 80.0


def test_bounding_box_spatial_operations():
    """Validates intersection, union, IoU, and contains."""
    b1 = BoundingBox(x1=0, y1=0, x2=10, y2=10)
    b2 = BoundingBox(x1=5, y1=5, x2=15, y2=15)
    b3 = BoundingBox(x1=20, y1=20, x2=30, y2=30)

    assert b1.intersects(b2)
    assert not b1.intersects(b3)

    inter = b1.intersection(b2)
    assert inter is not None
    assert inter.to_list() == [5, 5, 10, 10]
    assert inter.area == 25.0

    iou = b1.iou(b2)
    # inter = 25, union = 100 + 100 - 25 = 175 => 25/175 = 1/7
    assert pytest.approx(iou, 0.001) == 25.0 / 175.0

    enclosing = BoundingBox(x1=0, y1=0, x2=50, y2=50)
    assert enclosing.contains(b1)
    assert not b1.contains(enclosing)


def test_document_model_creation_and_reading_order():
    """Validates document structure, element addition, and natural reading order sorting."""
    doc = Document(metadata=DocumentMetadata(title="Test Document", author="Antigravity"))
    page = Page(page_number=1, width=595.0, height=842.0)

    # Add elements in mixed spatial order
    el_header = TextElement(
        bbox=BoundingBox(x1=50, y1=50, x2=300, y2=80),
        text="CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        bold=True,
        font_size=14.0,
    )
    el_body2 = TextElement(
        bbox=BoundingBox(x1=50, y1=150, x2=400, y2=170),
        text="Nội dung điều khoản thứ hai.",
    )
    el_body1 = TextElement(
        bbox=BoundingBox(x1=50, y1=100, x2=400, y2=120),
        text="Nội dung điều khoản thứ nhất.",
    )

    page.add_element(el_body2)
    page.add_element(el_header)
    page.add_element(el_body1)

    doc.add_page(page)

    assert doc.total_pages == 1
    assert doc.metadata.page_count == 1

    # Sorted reading order should be Header -> Body 1 -> Body 2
    sorted_elements = page.get_sorted_elements()
    assert sorted_elements[0].text == "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
    assert sorted_elements[1].text == "Nội dung điều khoản thứ nhất."
    assert sorted_elements[2].text == "Nội dung điều khoản thứ hai."

    full_text = doc.get_full_text()
    assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in full_text
    assert "Nội dung điều khoản thứ nhất." in full_text


def test_table_element_and_markdown():
    """Validates table element creation and markdown rendering."""
    cells = [
        TableCell(row_index=0, col_index=0, text="Mã số"),
        TableCell(row_index=0, col_index=1, text="Tên tài liệu"),
        TableCell(row_index=1, col_index=0, text="001"),
        TableCell(row_index=1, col_index=1, text="Hợp đồng lao động"),
    ]
    table = TableElement(
        bbox=BoundingBox(x1=50, y1=200, x2=450, y2=300),
        rows=2,
        columns=2,
        cells=cells,
        has_header=True,
    )

    matrix = table.to_matrix()
    assert matrix[0] == ["Mã số", "Tên tài liệu"]
    assert matrix[1] == ["001", "Hợp đồng lao động"]

    md = table.to_markdown()
    assert "| Mã số | Tên tài liệu |" in md
    assert "| 001 | Hợp đồng lao động |" in md


def test_document_json_serialization():
    """Validates serialization to/from JSON."""
    doc = Document(metadata=DocumentMetadata(title="Serializable Doc"))
    page = Page(page_number=1, width=600, height=800)
    page.add_element(
        TextElement(
            bbox=BoundingBox(x1=10, y1=10, x2=100, y2=30),
            text="Xin chào Việt Nam",
            confidence=0.99,
        )
    )
    doc.add_page(page)

    json_data = doc.to_json()
    assert "Xin chào Việt Nam" in json_data

    reloaded = Document.from_json(json_data)
    assert reloaded.metadata.title == "Serializable Doc"
    assert reloaded.total_pages == 1
    assert reloaded.pages[0].elements[0].text == "Xin chào Việt Nam"
    assert reloaded.pages[0].elements[0].confidence == 0.99


def test_file_type_detection_magic_bytes(tmp_path):
    """Validates file type detection for PDF, images, and DOCX."""
    # PDF
    pdf_bytes = b"%PDF-1.7 header test"
    assert detect_file_type(pdf_bytes) == FileType.PDF

    # PNG
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00"
    assert detect_file_type(png_bytes) == FileType.PNG

    # JPEG
    jpg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    assert detect_file_type(jpg_bytes) == FileType.JPEG

    # WEBP
    webp_bytes = b"RIFF\x24\x00\x00\x00WEBPVP8 "
    assert detect_file_type(webp_bytes) == FileType.WEBP

    # DOCX (zip with word/document.xml)
    docx_io = io.BytesIO()
    with zipfile.ZipFile(docx_io, "w") as zf:
        zf.writestr("word/document.xml", "<xml></xml>")
    docx_bytes = docx_io.getvalue()
    assert detect_file_type(docx_bytes) == FileType.DOCX

    # Fallback by file extension
    fake_txt = tmp_path / "notes.txt"
    fake_txt.write_text("plain text", encoding="utf-8")
    assert detect_file_type(fake_txt) == FileType.TXT


def test_exception_messages():
    """Validates custom exceptions format and message generation."""
    err = UnsupportedFormatError("xyz")
    assert "Unsupported file format: 'xyz'" in str(err)

    inv = InvalidDocumentError("broken.pdf", "EOF marker missing")
    assert "broken.pdf" in str(inv)
    assert "EOF marker missing" in str(inv)

    ocr_err = OCRProcessingError("Model failed", provider="PaddleOCR")
    assert "PaddleOCR" in str(ocr_err)
