"""PDF processing service utilizing PyMuPDF (Fitz).

Provides comprehensive PDF parsing into the Document Model, text vs scanned detection,
page rendering, merging, splitting, rotation, page extraction, and searchable PDF generation.
"""

from pathlib import Path
import re
from typing import List, Optional, Tuple, Union
import cv2
import numpy as np
import pymupdf
from PIL import Image

from app.config import config
from app.core.exceptions import InvalidDocumentError, OCRProcessingError
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
from app.models.enums import OCRMode
from app.core.cancellation import CancellationToken, OperationCancelledError
from app.services.ocr.ocr_service import OCRService, get_ocr_service
from app.services.pdf.analyzer import PDFType, analyze_pdf
from app.services.table.table_service import TableService


def get_system_font_path() -> Optional[str]:
    """Finds standard Unicode TrueType font on Windows."""
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibri.ttf"),
        Path("C:/Windows/Fonts/times.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


class PDFService:
    """Enterprise-grade PDF manipulation and parsing engine."""

    def __init__(
        self,
        ocr_service: Optional[OCRService] = None,
        table_service: Optional[TableService] = None,
    ) -> None:
        self.ocr_service = ocr_service or get_ocr_service()
        self.table_service = table_service or TableService()
        self.system_font = get_system_font_path()

    def parse_to_document(
        self,
        source: Union[str, Path, bytes],
        force_ocr: bool = False,
        mode: Union[OCRMode, str] = OCRMode.FAST,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> Document:
        """Parses a PDF into the intermediate Document model.

        Automatically differentiates between native text layers and scanned pages.
        Never executes unnecessary OCR on clean text layers unless force_ocr is True.
        """
        if isinstance(source, bytes):
            doc = pymupdf.open(stream=source, filetype="pdf")
            source_name = "memory.pdf"
        else:
            path = Path(source)
            if not path.exists():
                raise InvalidDocumentError(str(path), "File does not exist")
            if path.stat().st_size == 0:
                raise InvalidDocumentError(str(path), "File is empty (0 bytes)")
            try:
                doc = pymupdf.open(str(path))
            except Exception as e:
                raise InvalidDocumentError(str(path), f"Failed to open PDF: {e}")
            source_name = str(path)

        try:
            analysis = analyze_pdf(doc)
            doc_metadata = DocumentMetadata(
                title=analysis.title or Path(source_name).stem,
                author=analysis.author,
                source_path=source_name,
                source_format="pdf",
                page_count=len(doc),
                custom={"pdf_type": analysis.pdf_type.value},
            )
            document = Document(metadata=doc_metadata)

            for page_idx, page in enumerate(doc):
                if cancellation_token and cancellation_token.is_cancelled:
                    raise OperationCancelledError()

                page_num = page_idx + 1
                page_analysis = analysis.pages[page_idx]
                page_width = float(page.rect.width)
                page_height = float(page.rect.height)

                doc_page = Page(
                    page_number=page_num,
                    width=page_width,
                    height=page_height,
                    rotation=int(page.rotation),
                )

                # Determine if page requires OCR
                needs_ocr = force_ocr or page_analysis.is_scanned

                if needs_ocr:
                    logger.info(f"Page {page_num} detected as scanned or OCR forced. Running OCR pipeline ({mode})...")
                    self._populate_page_with_ocr(page, doc_page, mode=mode)
                else:
                    self._populate_page_from_text_layer(page, doc_page)

                document.add_page(doc_page)

            return document
        finally:
            doc.close()

    def _populate_page_from_text_layer(self, page: pymupdf.Page, doc_page: Page) -> None:
        """Extracts text elements, layout blocks, tables, and images from native PDF page."""
        # 1. Extract tables first with high fidelity (merged cells, header rows, col widths)
        detected_tables: List[TableElement] = []
        table_bboxes: List[BoundingBox] = []

        try:
            tabs = page.find_tables()
            for tab in tabs:
                tab_bbox = BoundingBox(
                    x1=float(tab.bbox[0]),
                    y1=float(tab.bbox[1]),
                    x2=float(tab.bbox[2]),
                    y2=float(tab.bbox[3]),
                )
                df_rows = tab.extract()
                if not df_rows:
                    continue

                num_rows = len(df_rows)
                num_cols = len(df_rows[0]) if num_rows > 0 else 0
                if num_rows == 0 or num_cols == 0:
                    continue

                # Detect header rows count
                h_rows = 1
                if tab.header and tab.header.bbox:
                    h_rows = sum(1 for r in tab.rows if r.bbox and r.bbox[3] <= tab.header.bbox[3] + 2)
                    if h_rows == 0:
                        h_rows = 1

                # Detect explicit column widths
                full_rows = [r for r in tab.rows if all(c is not None for c in r.cells)]
                if full_rows:
                    col_widths = [float(c[2] - c[0]) for c in full_rows[0].cells]
                else:
                    col_widths = [float(tab.bbox[2] - tab.bbox[0]) / num_cols] * num_cols

                cells: List[TableCell] = []
                covered = [[False for _ in range(num_cols)] for _ in range(num_rows)]

                for r in range(num_rows):
                    for c in range(num_cols):
                        if covered[r][c]:
                            continue
                        val = df_rows[r][c]
                        cell_bbox_cand = tab.rows[r].cells[c] if r < len(tab.rows) and c < len(tab.rows[r].cells) else None
                        if val is None and cell_bbox_cand is None:
                            continue

                        # Calculate horizontal span (col_span)
                        col_span = 1
                        while (c + col_span < num_cols and
                               not covered[r][c + col_span] and
                               df_rows[r][c + col_span] is None and
                               (r >= len(tab.rows) or tab.rows[r].cells[c + col_span] is None)):
                            col_span += 1

                        # Calculate vertical span (row_span)
                        row_span = 1
                        while r + row_span < num_rows:
                            all_none = True
                            for check_c in range(c, c + col_span):
                                val_below = df_rows[r + row_span][check_c]
                                bbox_below = tab.rows[r + row_span].cells[check_c] if (r + row_span) < len(tab.rows) and check_c < len(tab.rows[r + row_span].cells) else None
                                if covered[r + row_span][check_c] or val_below is not None or bbox_below is not None:
                                    all_none = False
                                    break
                            if all_none:
                                row_span += 1
                            else:
                                break

                        # Mark covered matrix
                        for dr in range(row_span):
                            for dc in range(col_span):
                                covered[r + dr][c + dc] = True

                        cell_text = str(val or "").strip()
                        cells.append(
                            TableCell(
                                row_index=r,
                                col_index=c,
                                row_span=row_span,
                                col_span=col_span,
                                text=cell_text,
                            )
                        )

                table_el = TableElement(
                    bbox=tab_bbox,
                    rows=num_rows,
                    columns=num_cols,
                    cells=cells,
                    has_header=True,
                    header_rows=h_rows,
                    col_widths=col_widths,
                )
                detected_tables.append(table_el)
                table_bboxes.append(tab_bbox)
                doc_page.add_element(table_el)

        except Exception as e:
            logger.debug(f"Table extraction skipped on page {page.number + 1}: {e}")

        # 2. Extract structured text blocks and spans (filtering out text inside tables to prevent duplication)
        page_dict = page.get_text("dict")
        for block in page_dict.get("blocks", []):
            b_type = block.get("type", 0)
            if b_type == 0:  # Text block
                bbox_list = block.get("bbox", [0, 0, 0, 0])
                for line in block.get("lines", []):
                    line_bbox = line.get("bbox", bbox_list)
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue

                        span_bbox = span.get("bbox", line_bbox)
                        bx1 = float(span_bbox[0])
                        by1 = float(span_bbox[1])
                        bx2 = float(span_bbox[2])
                        by2 = float(span_bbox[3])

                        # Skip text spans that are inside any detected table bounding box
                        cx = (bx1 + bx2) / 2.0
                        cy = (by1 + by2) / 2.0
                        is_inside_table = False
                        for t_box in table_bboxes:
                            if (t_box.x1 - 2.0 <= cx <= t_box.x2 + 2.0) and (t_box.y1 - 2.0 <= cy <= t_box.y2 + 2.0):
                                is_inside_table = True
                                break
                        if is_inside_table:
                            continue

                        font_size = float(span.get("size", 11.0))
                        font_name = str(span.get("font", "Arial"))
                        flags = span.get("flags", 0)

                        # Bit flags in PyMuPDF: bit 4 (16) is bold, bit 1 (2) is italic
                        is_bold = bool(flags & 16 or "bold" in font_name.lower())
                        is_italic = bool(flags & 2 or "italic" in font_name.lower())

                        # Color integer to Hex
                        color_int = span.get("color", 0)
                        hex_color = f"#{color_int:06x}" if isinstance(color_int, int) else "#000000"

                        # Alignment heuristic based on page width
                        b_center = (bx1 + bx2) / 2.0
                        page_center = doc_page.width / 2.0
                        alignment = TextAlignment.LEFT
                        if abs(b_center - page_center) < 30.0 and (bx2 - bx1) < (doc_page.width * 0.75):
                            alignment = TextAlignment.CENTER
                        elif bx2 > (doc_page.width - 70.0) and bx1 > (doc_page.width * 0.4):
                            alignment = TextAlignment.RIGHT

                        is_header = by2 < (doc_page.height * 0.08)
                        is_footer = by1 > (doc_page.height * 0.92)

                        doc_page.add_element(
                            TextElement(
                                text=text,
                                bbox=BoundingBox(x1=bx1, y1=by1, x2=bx2, y2=by2),
                                font_name=font_name,
                                font_size=font_size,
                                bold=is_bold,
                                italic=is_italic,
                                alignment=alignment,
                                color=hex_color,
                                is_header=is_header,
                                is_footer=is_footer,
                                confidence=1.0,
                            )
                        )

            elif b_type == 1:
                # Handled via high-fidelity xref extraction below
                pass

        # 3. Extract images with high-fidelity SMask / Alpha preservation & white background compositing
        try:
            from PIL import Image
            import io
            img_infos = page.get_image_info(xrefs=True)
            for info in img_infos:
                xref = info.get("xref", 0)
                bbox_list = info.get("bbox", [0, 0, 0, 0])
                if xref <= 0:
                    continue
                extracted = page.parent.extract_image(xref)
                if not extracted or not extracted.get("image"):
                    continue
                raw_bytes = extracted["image"]
                img = Image.open(io.BytesIO(raw_bytes))
                smask_xref = extracted.get("smask", 0)
                if smask_xref and smask_xref > 0:
                    try:
                        mask_extracted = page.parent.extract_image(smask_xref)
                        if mask_extracted and mask_extracted.get("image"):
                            mask_img = Image.open(io.BytesIO(mask_extracted["image"])).convert("L")
                            img = img.convert("RGB")
                            img.putalpha(mask_img)
                    except Exception as me:
                        logger.debug(f"Failed to apply smask {smask_xref}: {me}")

                # If image has alpha/transparency, composite onto pure white background
                # to prevent black background rendering in Microsoft Word / viewers
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                    img = Image.alpha_composite(bg, img.convert("RGBA")).convert("RGB")
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                png_bytes = buf.getvalue()

                doc_page.add_element(
                    ImageElement(
                        bbox=BoundingBox(
                            x1=float(bbox_list[0]),
                            y1=float(bbox_list[1]),
                            x2=float(bbox_list[2]),
                            y2=float(bbox_list[3]),
                        ),
                        image_data=png_bytes,
                        format="png",
                    )
                )
        except Exception as e:
            logger.warning(f"Advanced image extraction failed on page {page.number + 1}: {e}")

        # 4. Adaptively compute page margins from content elements
        if doc_page.elements:
            min_x = min(el.bbox.x1 for el in doc_page.elements)
            max_x = max(el.bbox.x2 for el in doc_page.elements)
            min_y = min(el.bbox.y1 for el in doc_page.elements)
            max_y = max(el.bbox.y2 for el in doc_page.elements)
            doc_page.margin_left = max(24.0, min(72.0, min_x))
            doc_page.margin_right = max(24.0, min(72.0, doc_page.width - max_x))
            doc_page.margin_top = max(24.0, min(72.0, min_y))
            doc_page.margin_bottom = max(24.0, min(72.0, doc_page.height - max_y))

    def _populate_page_with_ocr(
        self,
        page: pymupdf.Page,
        doc_page: Page,
        mode: Union[OCRMode, str] = OCRMode.FAST,
    ) -> None:
        """Renders page as image, executes OCR, and scales coordinates to match PDF page."""
        dpi = config.pdf.render_dpi
        pix = page.get_pixmap(dpi=dpi)
        # Convert pixmap to numpy BGR image
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if pix.n == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        elif pix.n == 1:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
        elif pix.n == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # Scale factor from pixel coordinates to PDF point coordinates (72 points per inch)
        scale_x = doc_page.width / float(pix.width)
        scale_y = doc_page.height / float(pix.height)

        ocr_elements = self.ocr_service.recognize_image(
            source=img_array,
            mode=mode,
            preprocess=True,
            deskew=True,
            enhance=True,
        )

        for el in ocr_elements:
            scaled_bbox = el.bbox.scale(scale_x, scale_y)
            doc_page.add_element(
                TextElement(
                    text=el.text,
                    bbox=scaled_bbox,
                    font_size=scaled_bbox.height * 0.75,
                    confidence=el.confidence,
                )
            )

    def render_page_to_image(
        self,
        source: Union[str, Path, bytes],
        page_number: int = 1,
        dpi: int = 300,
    ) -> np.ndarray:
        """Renders a specific PDF page to an OpenCV BGR image."""
        if isinstance(source, bytes):
            doc = pymupdf.open(stream=source, filetype="pdf")
        else:
            doc = pymupdf.open(str(source))

        try:
            if page_number < 1 or page_number > len(doc):
                raise InvalidDocumentError(
                    str(source),
                    f"Page {page_number} out of bounds (document has {len(doc)} pages)",
                )

            page = doc[page_number - 1]
            pix = page.get_pixmap(dpi=dpi)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
            if pix.n == 4:
                return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            elif pix.n == 1:
                return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            return img
        finally:
            doc.close()

    def merge_pdfs(
        self,
        pdf_paths: List[Union[str, Path]],
        output_path: Union[str, Path],
    ) -> Path:
        """Merges multiple PDF files in sequential order."""
        if not pdf_paths:
            raise InvalidDocumentError("merge", "No PDF files provided for merging")

        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        merged_doc = pymupdf.open()
        try:
            for p in pdf_paths:
                fpath = Path(p)
                if not fpath.exists():
                    raise InvalidDocumentError(str(fpath), "File to merge not found")
                with pymupdf.open(str(fpath)) as sub_doc:
                    merged_doc.insert_pdf(sub_doc)

            merged_doc.save(str(out_path))
            return out_path
        finally:
            merged_doc.close()

    def split_pdf(
        self,
        pdf_path: Union[str, Path],
        output_dir: Union[str, Path],
        page_ranges: Optional[str] = None,
        pages_per_split: int = 1,
    ) -> List[Path]:
        """Splits a PDF by page ranges or into chunks of pages.

        Example page_ranges: '1-3, 5, 7-10'. If None/empty and pages_per_split == 1,
        each page becomes an individual PDF. If pages_per_split > 1, batches of N pages
        are created.
        """
        fpath = Path(pdf_path)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        doc = pymupdf.open(str(fpath))
        created_files: List[Path] = []

        try:
            total_pages = len(doc)
            if total_pages == 0:
                return created_files

            if page_ranges and page_ranges.strip().lower() != "all":
                # Parse range string: e.g. "1-3, 5, 7-10"
                ranges = [r.strip() for r in page_ranges.split(",") if r.strip()]
                for r_idx, r_str in enumerate(ranges):
                    if "-" in r_str:
                        parts = r_str.split("-")
                        start = max(1, int(parts[0].strip()))
                        end = min(total_pages, int(parts[1].strip()))
                    else:
                        start = end = int(r_str)

                    if start > end or start > total_pages:
                        continue

                    range_doc = pymupdf.open()
                    range_doc.insert_pdf(doc, from_page=start - 1, to_page=end - 1)
                    if start == end:
                        out_file = out_dir / f"{fpath.stem}_page_{start}.pdf"
                    else:
                        out_file = out_dir / f"{fpath.stem}_split_{start}_{end}.pdf"
                    range_doc.save(str(out_file))
                    range_doc.close()
                    created_files.append(out_file)
                return created_files

            # Pages per split (default 1)
            chunk_size = max(1, pages_per_split)
            for i in range(0, total_pages, chunk_size):
                start = i
                end = min(i + chunk_size - 1, total_pages - 1)
                single_doc = pymupdf.open()
                single_doc.insert_pdf(doc, from_page=start, to_page=end)
                if chunk_size == 1:
                    out_file = out_dir / f"{fpath.stem}_page_{start + 1}.pdf"
                else:
                    out_file = out_dir / f"{fpath.stem}_part_{start + 1}_{end + 1}.pdf"
                single_doc.save(str(out_file))
                single_doc.close()
                created_files.append(out_file)

            return created_files
        finally:
            doc.close()

    def rotate_pages(
        self,
        pdf_path: Union[str, Path],
        output_path: Union[str, Path],
        degrees: int = 90,
        page_numbers: Optional[List[int]] = None,
    ) -> Path:
        """Rotates specified pages (or all pages) clockwise by 90, 180, or 270 degrees."""
        fpath = Path(pdf_path)
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        doc = pymupdf.open(str(fpath))
        try:
            target_indices = (
                [p - 1 for p in page_numbers if 1 <= p <= len(doc)]
                if page_numbers
                else list(range(len(doc)))
            )
            for idx in target_indices:
                page = doc[idx]
                page.set_rotation((page.rotation + degrees) % 360)

            doc.save(str(out_path))
            return out_path
        finally:
            doc.close()

    def extract_pages(
        self,
        pdf_path: Union[str, Path],
        output_path: Union[str, Path],
        pages: List[int],
    ) -> Path:
        """Extracts selected pages into a new PDF."""
        fpath = Path(pdf_path)
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        doc = pymupdf.open(str(fpath))
        new_doc = pymupdf.open()
        try:
            for p in pages:
                if 1 <= p <= len(doc):
                    new_doc.insert_pdf(doc, from_page=p - 1, to_page=p - 1)

            new_doc.save(str(out_path))
            return out_path
        finally:
            new_doc.close()
            doc.close()

    def create_searchable_pdf(
        self,
        source: Union[str, Path, bytes],
        output_path: Union[str, Path],
        lang: Optional[str] = None,
        mode: Union[OCRMode, str] = OCRMode.FAST,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> Path:
        """Converts an image or scanned PDF into a searchable PDF with exact OCR text positioning."""
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if source is image or PDF
        from app.utils.file_type import FileType, detect_file_type
        ftype = detect_file_type(source)

        pdf_doc = pymupdf.open()
        try:
            if ftype.is_image:
                if cancellation_token and cancellation_token.is_cancelled:
                    raise OperationCancelledError()

                # Single image input
                img_array = cv2.imread(str(source)) if isinstance(source, (str, Path)) else None
                if img_array is None:
                    from app.services.image.preprocessor import ImagePreprocessor
                    img_array = ImagePreprocessor.load_image(source)

                h, w = img_array.shape[:2]
                rect = pymupdf.Rect(0, 0, w, h)
                page = pdf_doc.new_page(width=w, height=h)

                # Embed background image
                success, buffer = cv2.imencode(".png", img_array)
                if success:
                    page.insert_image(rect, stream=buffer.tobytes())

                # Run OCR
                font_args = {"fontfile": self.system_font, "fontname": "arial"} if self.system_font else {}
                elements = self.ocr_service.recognize_image(img_array, mode=mode, lang=lang)
                for el in elements:
                    page.insert_text(
                        pymupdf.Point(el.bbox.x1, el.bbox.y2),
                        el.text,
                        fontsize=max(6.0, el.bbox.height * 0.75),
                        color=(0, 0, 0),
                        render_mode=3,  # Invisible text layer for searchability
                        **font_args,
                    )

            elif ftype == FileType.PDF:
                # Scanned PDF input: process each page
                in_doc = (
                    pymupdf.open(stream=source, filetype="pdf")
                    if isinstance(source, bytes)
                    else pymupdf.open(str(source))
                )
                try:
                    font_args = {"fontfile": self.system_font, "fontname": "arial"} if self.system_font else {}
                    for src_page in in_doc:
                        if cancellation_token and cancellation_token.is_cancelled:
                            raise OperationCancelledError()

                        dpi = config.pdf.render_dpi
                        pix = src_page.get_pixmap(dpi=dpi)
                        w, h = src_page.rect.width, src_page.rect.height

                        new_page = pdf_doc.new_page(width=w, height=h)
                        # Insert original page render as image
                        new_page.insert_image(src_page.rect, stream=pix.tobytes("png"))

                        # Run OCR on pixmap
                        img_arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
                        if pix.n >= 3:
                            img_arr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)

                        scale_x = w / float(pix.width)
                        scale_y = h / float(pix.height)
                        elements = self.ocr_service.recognize_image(img_arr, mode=mode, lang=lang)

                        for el in elements:
                            scaled = el.bbox.scale(scale_x, scale_y)
                            new_page.insert_text(
                                pymupdf.Point(scaled.x1, scaled.y2),
                                el.text,
                                fontsize=max(6.0, scaled.height * 0.75),
                                color=(0, 0, 0),
                                render_mode=3,
                                **font_args,
                            )
                finally:
                    in_doc.close()

            pdf_doc.save(str(out_path))
            return out_path
        finally:
            pdf_doc.close()
