"""Document Loader service with automatic file format detection.

Parses input files of various formats (PDF, DOCX, images, TXT) into the intermediate
Document model.
"""

from pathlib import Path
from typing import Optional, Union

from app.core.exceptions import InvalidDocumentError, UnsupportedFormatError
from app.models.document import Document, DocumentMetadata, Page
from app.models.elements import BoundingBox, TextElement
from app.models.enums import OCRMode
from app.core.cancellation import CancellationToken
from app.services.docx.docx_service import DOCXService
from app.services.ocr.ocr_service import OCRService, get_ocr_service
from app.services.pdf.pdf_service import PDFService
from app.utils.file_type import FileType, detect_file_type


class DocumentLoader:
    """Unified document loader and entry point."""

    def __init__(
        self,
        ocr_service: Optional[OCRService] = None,
        pdf_service: Optional[PDFService] = None,
        docx_service: Optional[DOCXService] = None,
    ) -> None:
        self.ocr_service = ocr_service or get_ocr_service()
        self.pdf_service = pdf_service or PDFService(ocr_service=self.ocr_service)
        self.docx_service = docx_service or DOCXService()

    def load(
        self,
        source: Union[str, Path, bytes],
        force_ocr: bool = False,
        lang: Optional[str] = None,
        mode: Union[OCRMode, str] = OCRMode.FAST,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> Document:
        """Loads a document or image file into the unified intermediate Document model.

        Args:
            source: File path or raw bytes.
            force_ocr: Forces OCR even if text layer exists.
            lang: Language code for OCR processing.
            mode: OCRMode (FAST, FULL, or AUTO). Defaults to FAST.
            cancellation_token: Optional token for cancellation.

        Returns:
            Document model instance.
        """
        if isinstance(source, (str, Path)):
            p = Path(source)
            if not p.exists():
                raise InvalidDocumentError(str(p), "File does not exist")
            if p.is_file() and p.stat().st_size == 0:
                raise InvalidDocumentError(str(p), "File is empty (0 bytes)")

        ftype = detect_file_type(source)

        if ftype == FileType.PDF:
            return self.pdf_service.parse_to_document(
                source,
                force_ocr=force_ocr,
                mode=mode,
                cancellation_token=cancellation_token,
            )

        elif ftype == FileType.DOCX:
            return self.docx_service.parse_to_document(source)

        elif ftype.is_image:
            return self.ocr_service.image_to_document(source, mode=mode, lang=lang)

        elif ftype in (FileType.TXT, FileType.MARKDOWN):
            return self._load_plain_text(source, ftype.value)

        elif ftype == FileType.HTML:
            return self.pdf_service.parse_to_document(
                source,
                force_ocr=force_ocr,
                mode=mode,
                cancellation_token=cancellation_token,
            )

        else:
            name = str(source) if isinstance(source, (str, Path)) else "bytes"
            raise UnsupportedFormatError(
                ftype.value,
                f"File '{name}' has unsupported or unknown format '{ftype.value}'.",
            )

    def _load_plain_text(self, source: Union[str, Path, bytes], format_name: str) -> Document:
        """Loads plain text or markdown files into Document model with proper A4 pagination."""
        import textwrap

        if isinstance(source, bytes):
            text_content = source.decode("utf-8", errors="replace")
            source_name = "memory.txt"
        else:
            path = Path(source)
            if not path.exists():
                raise InvalidDocumentError(str(path), "File does not exist")
            text_content = path.read_text(encoding="utf-8", errors="replace")
            source_name = str(path)

        page_width = 595.0
        page_height = 842.0
        margin_x = 50.0
        margin_y = 50.0
        max_y = page_height - margin_y
        line_height = 16.0

        doc = Document(
            metadata=DocumentMetadata(
                title=Path(source_name).stem,
                source_path=source_name,
                source_format=format_name,
                page_count=1,
            )
        )

        current_page_num = 1
        page = Page(page_number=current_page_num, width=page_width, height=page_height)
        lines = text_content.splitlines()
        current_y = margin_y

        for raw_line in lines:
            line_str = raw_line.rstrip()
            if not line_str:
                current_y += 10.0
                if current_y > max_y:
                    doc.add_page(page)
                    current_page_num += 1
                    page = Page(page_number=current_page_num, width=page_width, height=page_height)
                    current_y = margin_y
                continue

            # Wrap lines longer than 80 chars to fit standard page width
            wrapped = textwrap.wrap(line_str, width=80) if len(line_str) > 80 else [line_str]
            for sub_line in wrapped:
                if current_y + line_height > max_y:
                    doc.add_page(page)
                    current_page_num += 1
                    page = Page(page_number=current_page_num, width=page_width, height=page_height)
                    current_y = margin_y

                page.add_element(
                    TextElement(
                        text=sub_line,
                        bbox=BoundingBox(
                            x1=margin_x,
                            y1=current_y,
                            x2=page_width - margin_x,
                            y2=current_y + 13.0,
                        ),
                        font_size=11.0,
                    )
                )
                current_y += line_height

        if page.elements or not doc.pages:
            doc.add_page(page)

        doc.metadata.page_count = len(doc.pages)
        return doc

