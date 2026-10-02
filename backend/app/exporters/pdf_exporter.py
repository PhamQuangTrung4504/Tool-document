"""PDF document exporter utilizing PyMuPDF."""

from pathlib import Path
from typing import Union
import pymupdf

from app.exporters.base import BaseExporter
from app.models.document import Document
from app.models.elements import ImageElement, TableElement, TextElement
from app.services.pdf.pdf_service import get_system_font_path


class PDFExporter(BaseExporter):
    """Exports Document model to a PDF file."""

    def __init__(self) -> None:
        self.system_font = get_system_font_path()

    @property
    def target_format(self) -> str:
        return "pdf"

    def export(self, document: Document, output_path: Union[str, Path]) -> Path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        pdf_doc = pymupdf.open()
        font_kwargs = {"fontfile": self.system_font, "fontname": "arial"} if self.system_font else {}

        try:
            for page in document.pages:
                pdf_page = pdf_doc.new_page(width=page.width, height=page.height)

                for el in page.get_sorted_elements():
                    if isinstance(el, TextElement):
                        if not el.text.strip():
                            continue
                        f_size = el.font_size or 11.0
                        pos = pymupdf.Point(el.bbox.x1, el.bbox.y2)
                        pdf_page.insert_text(
                            pos,
                            el.text,
                            fontsize=f_size,
                            **font_kwargs,
                        )

                    elif isinstance(el, TableElement):
                        matrix = el.to_matrix()
                        if not matrix:
                            continue
                        row_h = el.bbox.height / max(1, el.rows)
                        col_w = el.bbox.width / max(1, el.columns)

                        for r_idx in range(el.rows):
                            for c_idx in range(el.columns):
                                cell_x = el.bbox.x1 + c_idx * col_w
                                cell_y = el.bbox.y1 + r_idx * row_h
                                rect = pymupdf.Rect(cell_x, cell_y, cell_x + col_w, cell_y + row_h)
                                # Draw cell border
                                pdf_page.draw_rect(rect, color=(0.7, 0.7, 0.7), width=0.5)
                                # Cell text
                                text = matrix[r_idx][c_idx] if r_idx < len(matrix) and c_idx < len(matrix[r_idx]) else ""
                                if text:
                                    pdf_page.insert_text(
                                        pymupdf.Point(cell_x + 4, cell_y + row_h - 4),
                                        text,
                                        fontsize=9.0,
                                        **font_kwargs,
                                    )

                    elif isinstance(el, ImageElement):
                        rect = pymupdf.Rect(el.bbox.x1, el.bbox.y1, el.bbox.x2, el.bbox.y2)
                        if el.image_data:
                            pdf_page.insert_image(rect, stream=el.image_data)
                        elif el.image_path and Path(el.image_path).exists():
                            pdf_page.insert_image(rect, filename=str(el.image_path))

            pdf_doc.save(str(out_path))
            return out_path
        finally:
            pdf_doc.close()
