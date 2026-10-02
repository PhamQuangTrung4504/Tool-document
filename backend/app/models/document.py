"""Intermediate Document representation.

This is the central representation decoupling Parsers/OCR engines from Exporters.
No format converter ever directly converts source to target; all flows must pass
through this Document model:
Input -> Parser/OCR -> Document -> Exporter -> Output.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from app.models.elements import (
    BaseElement,
    ImageElement,
    ShapeElement,
    TableElement,
    TextElement,
)


class DocumentMetadata(BaseModel):
    """Metadata attributes of a document."""
    title: Optional[str] = None
    author: Optional[str] = None
    creator: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    source_path: Optional[str] = None
    source_format: Optional[str] = None
    page_count: int = 0
    custom: Dict[str, Any] = Field(default_factory=dict)


class DocumentStyle(BaseModel):
    """Global document typography and layout styles."""
    default_font: str = "Arial"
    default_font_size: float = 12.0
    line_spacing: float = 1.15
    margin_top: float = 72.0      # 1 inch (72 points)
    margin_bottom: float = 72.0
    margin_left: float = 72.0
    margin_right: float = 72.0


DocumentAnyElement = Union[TextElement, ImageElement, TableElement, ShapeElement]


class Page(BaseModel):
    """Represents a single document page with physical dimensions and layout elements."""
    page_number: int = Field(..., ge=1, description="1-indexed page number")
    width: float = Field(..., gt=0.0, description="Page width in points")
    height: float = Field(..., gt=0.0, description="Page height in points")
    rotation: int = Field(default=0, description="Page rotation in degrees (0, 90, 180, 270)")
    margin_top: float = Field(default=72.0, description="Top margin in points")
    margin_bottom: float = Field(default=72.0, description="Bottom margin in points")
    margin_left: float = Field(default=72.0, description="Left margin in points")
    margin_right: float = Field(default=72.0, description="Right margin in points")
    elements: List[DocumentAnyElement] = Field(default_factory=list)

    @property
    def is_landscape(self) -> bool:
        """Returns True if page width is greater than height."""
        return self.width > self.height

    def add_element(self, element: DocumentAnyElement) -> None:
        """Appends an element to the page."""
        self.elements.append(element)

    def get_text_elements(self) -> List[TextElement]:
        """Returns all text elements on this page."""
        return [el for el in self.elements if isinstance(el, TextElement)]

    def get_images(self) -> List[ImageElement]:
        """Returns all image elements on this page."""
        return [el for el in self.elements if isinstance(el, ImageElement)]

    def get_tables(self) -> List[TableElement]:
        """Returns all table elements on this page."""
        return [el for el in self.elements if isinstance(el, TableElement)]

    def get_text(self, separator: str = "\n") -> str:
        """Extracts text content in natural reading order."""
        sorted_elements = self.get_sorted_elements()
        text_lines = []
        for el in sorted_elements:
            if isinstance(el, TextElement):
                if el.text.strip():
                    text_lines.append(el.text)
            elif isinstance(el, TableElement):
                md_table = el.to_markdown()
                if md_table:
                    text_lines.append(md_table)
        return separator.join(text_lines)

    def get_sorted_elements(self) -> List[DocumentAnyElement]:
        """Sorts page elements according to natural reading order.

        Handles:
        1. Headers (top margin) ordered first.
        2. Footers (bottom margin) ordered last.
        3. Body: Detects two-column layouts.
           - If 2 columns detected: processes column 1 (left) top-to-bottom, then column 2 (right) top-to-bottom.
           - Full-width elements retain vertical reading position.
           - Single-column body: line-band clustering by Y, then X.
        """
        if not self.elements:
            return []

        header_threshold = self.height * 0.08
        footer_threshold = self.height * 0.92

        headers: List[DocumentAnyElement] = []
        footers: List[DocumentAnyElement] = []
        body: List[DocumentAnyElement] = []

        for el in self.elements:
            if getattr(el, "is_header", False) or el.bbox.y2 <= header_threshold:
                headers.append(el)
            elif getattr(el, "is_footer", False) or el.bbox.y1 >= footer_threshold:
                footers.append(el)
            else:
                body.append(el)

        def sort_band(items: List[DocumentAnyElement], band_size: float = 6.0) -> List[DocumentAnyElement]:
            return sorted(items, key=lambda x: (round(x.bbox.y1 / band_size) * band_size, x.bbox.x1))

        sorted_headers = sort_band(headers)
        sorted_footers = sort_band(footers)
        sorted_body = self._sort_body_elements(body)

        return sorted_headers + sorted_body + sorted_footers

    def _sort_body_elements(self, elements: List[DocumentAnyElement]) -> List[DocumentAnyElement]:
        """Sorts body elements respecting single or multi-column layout."""
        if len(elements) < 4:
            return sorted(elements, key=lambda x: (round(x.bbox.y1 / 6.0) * 6.0, x.bbox.x1))

        mid_x = self.width / 2.0
        margin_gutter = 15.0

        left_col: List[DocumentAnyElement] = []
        right_col: List[DocumentAnyElement] = []
        full_width: List[DocumentAnyElement] = []

        for el in elements:
            if el.bbox.width > self.width * 0.65:
                full_width.append(el)
            elif el.bbox.x2 <= mid_x + margin_gutter:
                left_col.append(el)
            elif el.bbox.x1 >= mid_x - margin_gutter:
                right_col.append(el)
            else:
                full_width.append(el)

        # Detect 2-column layout: both sides must have at least 2 elements with vertical overlap
        if len(left_col) >= 2 and len(right_col) >= 2:
            left_y_min, left_y_max = min(e.bbox.y1 for e in left_col), max(e.bbox.y2 for e in left_col)
            right_y_min, right_y_max = min(e.bbox.y1 for e in right_col), max(e.bbox.y2 for e in right_col)

            overlap_top = max(left_y_min, right_y_min)
            overlap_bottom = min(left_y_max, right_y_max)

            if overlap_bottom > overlap_top:
                sorted_left = sorted(left_col, key=lambda x: (round(x.bbox.y1 / 6.0) * 6.0, x.bbox.x1))
                sorted_right = sorted(right_col, key=lambda x: (round(x.bbox.y1 / 6.0) * 6.0, x.bbox.x1))

                if not full_width:
                    return sorted_left + sorted_right

                # Merge full-width banners with columns preserving vertical order
                merged: List[DocumentAnyElement] = []
                remaining_left = list(sorted_left)
                remaining_right = list(sorted_right)
                sorted_full = sorted(full_width, key=lambda x: x.bbox.y1)

                for fw in sorted_full:
                    # Flush elements above this full-width item
                    while remaining_left and remaining_left[0].bbox.y2 <= fw.bbox.y1:
                        merged.append(remaining_left.pop(0))
                    while remaining_right and remaining_right[0].bbox.y2 <= fw.bbox.y1:
                        merged.append(remaining_right.pop(0))
                    merged.append(fw)

                merged.extend(remaining_left)
                merged.extend(remaining_right)
                return merged

        return sorted(elements, key=lambda x: (round(x.bbox.y1 / 6.0) * 6.0, x.bbox.x1))


class Document(BaseModel):
    """The central unified document object model.

    Decouples all inputs and outputs. Any document format is parsed into this model,
    and any exporter serializes from this model.
    """
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    pages: List[Page] = Field(default_factory=list)
    styles: DocumentStyle = Field(default_factory=DocumentStyle)

    @property
    def total_pages(self) -> int:
        return len(self.pages)

    def add_page(self, page: Page) -> None:
        """Adds a page to the document and updates metadata page count."""
        self.pages.append(page)
        self.metadata.page_count = len(self.pages)

    def get_page(self, page_number: int) -> Optional[Page]:
        """Retrieves a page by its 1-indexed page number."""
        for page in self.pages:
            if page.page_number == page_number:
                return page
        return None

    def get_full_text(self, page_separator: str = "\n\n--- Page Break ---\n\n") -> str:
        """Extracts full document text across all pages."""
        return page_separator.join(
            page.get_text() for page in self.pages if page.get_text().strip()
        )

    def to_json(self, indent: int = 2) -> str:
        """Serializes document model to JSON string."""
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> Document:
        """Deserializes document model from JSON string."""
        return cls.model_validate_json(json_str)
