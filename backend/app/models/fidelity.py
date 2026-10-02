"""Document Fidelity Report model for objective quality metrics."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class DocumentFidelityReport(BaseModel):
    """Objective, non-subjective fidelity metrics assessing conversion integrity."""

    source_pages: int = Field(default=0, description="Total pages in source document")
    output_pages: int = Field(default=0, description="Total pages in converted output")
    source_text_chars: int = Field(default=0, description="Character count in source document")
    output_text_chars: int = Field(default=0, description="Character count in target output")
    text_coverage: float = Field(
        default=1.0,
        ge=0.0,
        description="Ratio of output text characters to source text characters",
    )
    ocr_confidence_avg: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Average OCR confidence across all recognized text elements",
    )
    tables_detected: int = Field(default=0, description="Number of structured tables recognized")
    images_detected: int = Field(default=0, description="Number of images recognized")
    element_count: int = Field(default=0, description="Total layout elements across all pages")
    bounding_box_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of total page area occupied by content bounding boxes",
    )
    warnings: List[str] = Field(default_factory=list, description="Objective diagnostic warnings")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes report to dictionary."""
        return self.model_dump()
