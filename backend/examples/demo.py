"""Demonstration script showcasing Document Assistant Backend features."""

from pathlib import Path
import sys

# Ensure backend root is on Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.document import Document, DocumentMetadata, Page
from app.models.elements import BoundingBox, TextElement, TableElement, TableCell, TextAlignment
from app.services.converter.converter_service import ConversionService
from app.services.docx.docx_service import DOCXService
from app.services.pdf.pdf_service import PDFService
from app.services.batch.batch_processor import BatchProcessor
from app.services.document.loader import DocumentLoader
from app.exporters import get_exporter


def run_demo():
    print("=== Document Assistant Backend Demo ===\n")
    demo_dir = Path("temp_demo")
    demo_dir.mkdir(exist_ok=True)

    # 1. Build a Document Model programmatically
    print("1. Creating in-memory Document Model...")
    doc = Document(metadata=DocumentMetadata(title="Văn Bản Hướng Dẫn Kỹ Thuật", author="Senior Architect"))
    page1 = Page(page_number=1, width=595.0, height=842.0)

    # Title
    page1.add_element(
        TextElement(
            bbox=BoundingBox(x1=50, y1=50, x2=545, y2=85),
            text="HỆ THỐNG XỬ LÝ TÀI LIỆU OFFLINE",
            font_size=16.0,
            bold=True,
            alignment=TextAlignment.CENTER,
        )
    )

    # Paragraph
    page1.add_element(
        TextElement(
            bbox=BoundingBox(x1=50, y1=100, x2=545, y2=130),
            text="Đây là tài liệu được sinh tự động thông qua Document Model trung gian.",
            font_size=11.0,
        )
    )

    # Table
    cells = [
        TableCell(row_index=0, col_index=0, text="Mã Chức Năng"),
        TableCell(row_index=0, col_index=1, text="Tên Module"),
        TableCell(row_index=1, col_index=0, text="MOD-01"),
        TableCell(row_index=1, col_index=1, text="PDF Parsing & Rendering"),
        TableCell(row_index=2, col_index=0, text="MOD-02"),
        TableCell(row_index=2, col_index=1, text="PaddleOCR Vietnamese Engine"),
    ]
    page1.add_element(
        TableElement(
            bbox=BoundingBox(x1=50, y1=150, x2=500, y2=250),
            rows=3,
            columns=2,
            cells=cells,
            has_header=True,
        )
    )
    doc.add_page(page1)
    print("   Document created with 1 page and", len(page1.elements), "elements.")

    # 2. Export to DOCX, PDF, HTML, Markdown, TXT
    print("\n2. Exporting Document Model to multiple formats...")
    for fmt in ["docx", "pdf", "html", "md", "txt"]:
        exporter = get_exporter(fmt)
        out_p = demo_dir / f"demo_output.{fmt}"
        exporter.export(doc, out_p)
        print(f"   [+] Exported: {out_p.name} ({out_p.stat().st_size} bytes)")

    # 3. PDF Operations: Merge & Split
    print("\n3. Testing PDF Merging and Splitting...")
    pdf_svc = PDFService()
    pdf1 = demo_dir / "demo_output.pdf"
    merged_pdf = demo_dir / "merged_demo.pdf"
    pdf_svc.merge_pdfs([pdf1, pdf1], merged_pdf)
    print(f"   [+] Merged 2 PDFs -> {merged_pdf.name} (pages: 2)")

    split_dir = demo_dir / "split_pages"
    splits = pdf_svc.split_pdf(merged_pdf, split_dir, page_ranges="1")
    print(f"   [+] Split PDF -> {len(splits)} file(s) in {split_dir.name}")

    print("\n=== Demo Complete! All operations succeeded locally on Windows. ===")


if __name__ == "__main__":
    run_demo()
