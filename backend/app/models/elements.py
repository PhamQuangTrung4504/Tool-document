"""Document elements representation (Text, Image, Table, Shape).

Represents individual components extracted from documents or OCR with spatial
positioning, typographic properties, and semantic attributes.
"""

from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional
from pydantic import BaseModel, Field

from app.models.geometry import BoundingBox


class TextAlignment(str, Enum):
    """Text horizontal alignment."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"


class ShapeType(str, Enum):
    """Geometric shape types."""
    RECTANGLE = "rectangle"
    LINE = "line"
    CIRCLE = "circle"
    PATH = "path"


class BaseElement(BaseModel):
    """Abstract base element with spatial bounding box."""
    bbox: BoundingBox
    id: Optional[str] = None
    z_index: int = 0


class TextElement(BaseElement):
    """Represents a text line, word, or block with typographic properties."""
    text: str = Field(..., description="Text content")
    font_name: Optional[str] = Field(default=None, description="Font family name")
    font_size: Optional[float] = Field(default=None, description="Font size in points")
    bold: bool = Field(default=False, description="Whether text is bold")
    italic: bool = Field(default=False, description="Whether text is italic")
    underline: bool = Field(default=False, description="Whether text is underlined")
    alignment: TextAlignment = Field(default=TextAlignment.LEFT, description="Horizontal text alignment")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="OCR recognition confidence score [0.0 - 1.0]")
    rotation: float = Field(default=0.0, description="Rotation angle in degrees")
    color: Optional[str] = Field(default="#000000", description="Hex text color code")
    line_spacing: Optional[float] = Field(default=1.0, description="Relative line height")
    space_before: float = Field(default=0.0, description="Spacing before paragraph in points")
    space_after: float = Field(default=0.0, description="Spacing after paragraph in points")
    is_header: bool = Field(default=False, description="Whether element is in page header area")
    is_footer: bool = Field(default=False, description="Whether element is in page footer area")

    def is_heading(self) -> bool:
        """Heuristic check if this element is likely a section heading."""
        if self.font_size and self.font_size > 14.0:
            return True
        return self.bold and len(self.text.strip()) < 80


class ImageElement(BaseElement):
    """Represents an embedded raster or vector image."""
    image_data: Optional[bytes] = Field(default=None, description="Raw image bytes in memory")
    image_path: Optional[Path] = Field(default=None, description="Path to extracted or cached image file")
    format: str = Field(default="png", description="Image format (png, jpeg, webp)")
    rotation: float = Field(default=0.0, description="Image rotation angle in degrees")
    description: Optional[str] = Field(default=None, description="Optional caption or alt-text")


class TableCell(BaseModel):
    """Represents a single cell in a TableElement."""
    row_index: int = Field(..., ge=0)
    col_index: int = Field(..., ge=0)
    row_span: int = Field(default=1, ge=1)
    col_span: int = Field(default=1, ge=1)
    text: str = Field(default="")
    elements: List[TextElement] = Field(default_factory=list)
    bbox: Optional[BoundingBox] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Cell detection/OCR confidence score [0.0 - 1.0]")


class TableElement(BaseElement):
    """Represents a structured table with rows, columns, and cells."""
    rows: int = Field(..., ge=1, description="Total number of rows")
    columns: int = Field(..., ge=1, description="Total number of columns")
    cells: List[TableCell] = Field(default_factory=list, description="List of cells in the table")
    has_header: bool = Field(default=False, description="Whether the first row is a header")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Table detection confidence score [0.0 - 1.0]")

    def get_cell(self, row: int, col: int) -> Optional[TableCell]:
        """Finds cell at specified (row, col) coordinates."""
        for cell in self.cells:
            if cell.row_index == row and cell.col_index == col:
                return cell
        return None

    def to_matrix(self) -> List[List[str]]:
        """Converts table cells into a 2D string matrix."""
        matrix = [["" for _ in range(self.columns)] for _ in range(self.rows)]
        for cell in self.cells:
            if 0 <= cell.row_index < self.rows and 0 <= cell.col_index < self.columns:
                matrix[cell.row_index][cell.col_index] = cell.text
        return matrix

    def to_markdown(self) -> str:
        """Renders table as a Markdown string."""
        matrix = self.to_matrix()
        if not matrix:
            return ""

        lines = []
        # Header row
        header = "| " + " | ".join(matrix[0]) + " |"
        separator = "| " + " | ".join(["---"] * self.columns) + " |"
        lines.append(header)
        lines.append(separator)

        for row in matrix[1:]:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)


class ShapeElement(BaseElement):
    """Represents a geometric vector shape (line, rectangle, etc.)."""
    shape_type: ShapeType = Field(default=ShapeType.RECTANGLE)
    stroke_color: Optional[str] = Field(default="#000000")
    fill_color: Optional[str] = Field(default=None)
    stroke_width: float = Field(default=1.0)
