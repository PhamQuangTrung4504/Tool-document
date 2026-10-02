"""PDF structural and content analyzer.

Determines whether a PDF contains an embedded text layer, is purely scanned/image-based,
or has mixed content across different pages.
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional, Union
import pymupdf
from pydantic import BaseModel, Field

from app.config import config
from app.core.exceptions import InvalidDocumentError


class PDFType(str, Enum):
    """Classification of PDF document content."""
    TEXT_BASED = "text_based"
    SCANNED = "scanned"
    MIXED = "mixed"


class PDFPageAnalysis(BaseModel):
    """Analysis for an individual PDF page."""
    page_number: int
    char_count: int
    image_count: int
    width: float
    height: float
    is_scanned: bool


class PDFAnalysisResult(BaseModel):
    """Overall document analysis result."""
    pdf_type: PDFType
    total_pages: int
    pages: List[PDFPageAnalysis] = Field(default_factory=list)
    title: Optional[str] = None
    author: Optional[str] = None


def analyze_pdf(
    source: Union[str, Path, bytes, pymupdf.Document],
    threshold_chars: int = 40,
) -> PDFAnalysisResult:
    """Inspects a PDF document to classify text vs scanned pages.

    Args:
        source: PDF path, bytes, or open pymupdf Document.
        threshold_chars: Character count below which a page containing images is deemed scanned.

    Returns:
        PDFAnalysisResult with page breakdown and classification.
    """
    should_close = False
    if isinstance(source, pymupdf.Document):
        doc = source
    elif isinstance(source, bytes):
        doc = pymupdf.open(stream=source, filetype="pdf")
        should_close = True
    else:
        path = Path(source)
        if not path.exists():
            raise InvalidDocumentError(str(path), "PDF file not found")
        try:
            doc = pymupdf.open(str(path))
            should_close = True
        except Exception as e:
            raise InvalidDocumentError(str(path), f"Failed to open PDF: {e}")

    try:
        pages_analysis: List[PDFPageAnalysis] = []
        scanned_count = 0
        text_count = 0

        for i, page in enumerate(doc):
            text = page.get_text().strip()
            char_count = len(text)
            images = page.get_images()
            image_count = len(images)

            # Heuristic: If char count is negligible and page has images, it's a scanned page
            is_scanned = (char_count < threshold_chars) and (image_count > 0 or char_count == 0)

            if is_scanned:
                scanned_count += 1
            else:
                text_count += 1

            pages_analysis.append(
                PDFPageAnalysis(
                    page_number=i + 1,
                    char_count=char_count,
                    image_count=image_count,
                    width=page.rect.width,
                    height=page.rect.height,
                    is_scanned=is_scanned,
                )
            )

        total = len(doc)
        if total == 0:
            pdf_type = PDFType.SCANNED
        elif scanned_count == total:
            pdf_type = PDFType.SCANNED
        elif text_count == total:
            pdf_type = PDFType.TEXT_BASED
        else:
            pdf_type = PDFType.MIXED

        metadata = doc.metadata or {}
        return PDFAnalysisResult(
            pdf_type=pdf_type,
            total_pages=total,
            pages=pages_analysis,
            title=metadata.get("title") or None,
            author=metadata.get("author") or None,
        )
    finally:
        if should_close:
            doc.close()
