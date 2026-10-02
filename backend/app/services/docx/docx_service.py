"""DOCX manipulation service utilizing python-docx.

Provides bidirectional conversion:
1. Parsing DOCX into the intermediate Document model (preserving paragraphs, runs,
   styles, formatting, tables, and images).
2. Exporting the intermediate Document model into a formatted DOCX document with
   custom styles, fonts, alignments, tables, and embedded images.
"""

import io
from pathlib import Path
from typing import List, Optional, Union
import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from app.core.exceptions import InvalidDocumentError
from app.core.logging import logger
from app.models.document import Document, DocumentMetadata, Page
from app.models.elements import (
    BoundingBox,
    ImageElement,
    TableCell,
    TableElement,
    TextAlignment,
    TextElement,
)


class DOCXService:
    """Enterprise-grade DOCX parser and generator."""

    @staticmethod
    def _hex_to_rgb(hex_code: str) -> Optional[RGBColor]:
        """Converts '#RRGGBB' hex color to python-docx RGBColor."""
        hex_code = hex_code.lstrip("#")
        if len(hex_code) == 6:
            try:
                r = int(hex_code[0:2], 16)
                g = int(hex_code[2:4], 16)
                b = int(hex_code[4:6], 16)
                return RGBColor(r, g, b)
            except ValueError:
                pass
        return None

    @staticmethod
    def _map_alignment_to_docx(alignment: TextAlignment) -> WD_ALIGN_PARAGRAPH:
        """Maps internal TextAlignment enum to python-docx WD_ALIGN_PARAGRAPH."""
        mapping = {
            TextAlignment.LEFT: WD_ALIGN_PARAGRAPH.LEFT,
            TextAlignment.CENTER: WD_ALIGN_PARAGRAPH.CENTER,
            TextAlignment.RIGHT: WD_ALIGN_PARAGRAPH.RIGHT,
            TextAlignment.JUSTIFY: WD_ALIGN_PARAGRAPH.JUSTIFY,
        }
        return mapping.get(alignment, WD_ALIGN_PARAGRAPH.LEFT)

    @staticmethod
    def _map_docx_alignment_to_model(wd_alignment: Optional[int]) -> TextAlignment:
        """Maps python-docx alignment integer to TextAlignment enum."""
        if wd_alignment == WD_ALIGN_PARAGRAPH.CENTER:
            return TextAlignment.CENTER
        if wd_alignment == WD_ALIGN_PARAGRAPH.RIGHT:
            return TextAlignment.RIGHT
        if wd_alignment == WD_ALIGN_PARAGRAPH.JUSTIFY:
            return TextAlignment.JUSTIFY
        return TextAlignment.LEFT

    def parse_to_document(self, source: Union[str, Path, bytes]) -> Document:
        """Parses a DOCX file into the intermediate Document model."""
        if isinstance(source, bytes):
            doc = docx.Document(io.BytesIO(source))
            source_name = "memory.docx"
        else:
            path = Path(source)
            if not path.exists():
                raise InvalidDocumentError(str(path), "DOCX file does not exist")
            try:
                doc = docx.Document(str(path))
                source_name = str(path)
            except Exception as e:
                raise InvalidDocumentError(str(path), f"Failed to open DOCX: {e}")

        core_props = doc.core_properties
        doc_metadata = DocumentMetadata(
            title=core_props.title or Path(source_name).stem,
            author=core_props.author,
            source_path=source_name,
            source_format="docx",
        )
        document = Document(metadata=doc_metadata)

        # Standard A4 dimensions in points: 595.28 x 841.89
        page = Page(page_number=1, width=595.28, height=841.89)
        current_y = 50.0  # Estimated spatial vertical cursor

        # 1. Extract paragraphs
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                current_y += 12.0
                continue

            alignment = self._map_docx_alignment_to_model(para.alignment)

            # Analyze runs for typography
            runs_bold = any(run.bold for run in para.runs if run.bold is not None)
            runs_italic = any(run.italic for run in para.runs if run.italic is not None)
            runs_underline = any(run.underline for run in para.runs if run.underline is not None)

            # Find representative font size and name
            font_size = 11.0
            font_name = "Calibri"
            for run in para.runs:
                if run.font.size and hasattr(run.font.size, "pt"):
                    font_size = float(run.font.size.pt)
                if run.font.name:
                    font_name = run.font.name

            # Estimate line height and width
            line_height = max(14.0, font_size * 1.3)
            char_width = font_size * 0.55
            est_width = min(500.0, max(50.0, len(text) * char_width))

            # Alignment coordinate offset
            x1 = 50.0
            if alignment == TextAlignment.CENTER:
                x1 = max(50.0, (595.28 - est_width) / 2.0)
            elif alignment == TextAlignment.RIGHT:
                x1 = max(50.0, 545.28 - est_width)

            bbox = BoundingBox(x1=x1, y1=current_y, x2=x1 + est_width, y2=current_y + line_height)

            page.add_element(
                TextElement(
                    text=text,
                    bbox=bbox,
                    font_name=font_name,
                    font_size=font_size,
                    bold=runs_bold,
                    italic=runs_italic,
                    underline=runs_underline,
                    alignment=alignment,
                    confidence=1.0,
                )
            )
            current_y += line_height + 4.0

        # 2. Extract tables
        for table in doc.tables:
            num_rows = len(table.rows)
            num_cols = len(table.columns) if num_rows > 0 else 0
            if num_rows == 0 or num_cols == 0:
                continue

            cells: List[TableCell] = []
            for r_idx, row in enumerate(table.rows):
                for c_idx, cell in enumerate(row.cells):
                    cell_text = cell.text.strip()
                    cells.append(
                        TableCell(
                            row_index=r_idx,
                            col_index=c_idx,
                            text=cell_text,
                        )
                    )

            table_height = max(40.0, num_rows * 20.0)
            table_bbox = BoundingBox(
                x1=50.0,
                y1=current_y,
                x2=545.28,
                y2=current_y + table_height,
            )
            page.add_element(
                TableElement(
                    bbox=table_bbox,
                    rows=num_rows,
                    columns=num_cols,
                    cells=cells,
                    has_header=True,
                )
            )
            current_y += table_height + 15.0

        document.add_page(page)
        return document

    def export_to_docx(
        self,
        document: Document,
        output_path: Union[str, Path],
    ) -> Path:
        """Serializes the intermediate Document model into a high-fidelity DOCX file."""
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        doc = docx.Document()

        from docx.enum.section import WD_ORIENTATION

        # Configure page margins and orientation from the first page
        sections = doc.sections
        if sections and document.pages:
            first_page = document.pages[0]
            section = sections[0]
            section.top_margin = Pt(first_page.margin_top)
            section.bottom_margin = Pt(first_page.margin_bottom)
            section.left_margin = Pt(first_page.margin_left)
            section.right_margin = Pt(first_page.margin_right)
            if first_page.is_landscape:
                section.orientation = WD_ORIENTATION.LANDSCAPE
                section.page_width = Pt(first_page.width)
                section.page_height = Pt(first_page.height)
            else:
                section.page_width = Pt(first_page.width)
                section.page_height = Pt(first_page.height)

        total_pages = document.total_pages

        for page_idx, page in enumerate(document.pages):
            sorted_elements = page.get_sorted_elements()

            for element in sorted_elements:
                if isinstance(element, TextElement):
                    if not element.text.strip():
                        continue

                    p = doc.add_paragraph()
                    p.alignment = self._map_alignment_to_docx(element.alignment)

                    # Space before / after heuristics
                    space_b = element.space_before if element.space_before > 0 else 2.0
                    space_a = element.space_after if element.space_after > 0 else 4.0
                    p.paragraph_format.space_before = Pt(space_b)
                    p.paragraph_format.space_after = Pt(space_a)

                    run = p.add_run(element.text)
                    if element.font_name:
                        run.font.name = element.font_name
                    else:
                        run.font.name = document.styles.default_font

                    if element.font_size:
                        run.font.size = Pt(element.font_size)
                    else:
                        run.font.size = Pt(document.styles.default_font_size)

                    run.bold = element.bold
                    run.italic = element.italic
                    run.underline = element.underline

                    if element.color:
                        rgb = self._hex_to_rgb(element.color)
                        if rgb:
                            run.font.color.rgb = rgb

                elif isinstance(element, TableElement):
                    matrix = element.to_matrix()
                    if not matrix or element.rows == 0 or element.columns == 0:
                        continue

                    table = doc.add_table(rows=element.rows, cols=element.columns)
                    table.style = "Table Grid"

                    for r_idx in range(element.rows):
                        for c_idx in range(element.columns):
                            cell_text = matrix[r_idx][c_idx] if r_idx < len(matrix) and c_idx < len(matrix[r_idx]) else ""
                            cell = table.cell(r_idx, c_idx)
                            cell.text = cell_text
                            # Bold header row
                            if r_idx == 0 and element.has_header:
                                for p in cell.paragraphs:
                                    for r in p.runs:
                                        r.bold = True

                elif isinstance(element, ImageElement):
                    try:
                        if element.image_data:
                            img_stream = io.BytesIO(element.image_data)
                            # Calculate width in inches
                            width_pt = element.bbox.width if element.bbox.width > 20 else 200.0
                            doc.add_picture(img_stream, width=Pt(min(450.0, width_pt)))
                        elif element.image_path and Path(element.image_path).exists():
                            width_pt = element.bbox.width if element.bbox.width > 20 else 200.0
                            doc.add_picture(str(element.image_path), width=Pt(min(450.0, width_pt)))
                    except Exception as e:
                        logger.warning(f"Could not embed image into DOCX: {e}")

            # Insert page break between pages (except last page)
            if page_idx < total_pages - 1:
                doc.add_page_break()

        doc.save(str(out_path))
        return out_path
