"""Application configuration settings for Document Assistant Backend.

Manages offline runtime configurations, default parameters, and directory paths.
"""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class OCRConfig(BaseModel):
    """Configuration for OCR processing."""

    default_language: str = Field(default="vi", description="Default OCR language (e.g. 'vi', 'en')")
    fallback_language: str = Field(default="en", description="Fallback OCR language")
    confidence_threshold: float = Field(default=0.5, description="Minimum confidence score to accept OCR text")
    use_angle_cls: bool = Field(default=True, description="Enable orientation/angle classification")
    det_db_thresh: float = Field(default=0.3, description="Detection threshold for text boxes")
    det_db_box_thresh: float = Field(default=0.6, description="Bounding box score threshold")
    enable_gpu: bool = Field(default=False, description="Whether to run OCR with GPU acceleration if available")


class PreprocessingConfig(BaseModel):
    """Configuration for image preprocessing pipeline."""

    auto_deskew: bool = Field(default=True, description="Automatically correct text tilt/deskew")
    auto_denoise: bool = Field(default=True, description="Apply denoising filter to noisy scans")
    auto_contrast: bool = Field(default=True, description="Enhance contrast for faint text")
    auto_threshold: bool = Field(default=False, description="Apply adaptive binarization threshold")
    cleanup_border: bool = Field(default=False, description="Trim dark borders from scanned pages")
    max_image_dimension: int = Field(default=4000, description="Resize image if width or height exceeds this limit")


class PDFConfig(BaseModel):
    """Configuration for PDF parsing and rendering."""

    render_dpi: int = Field(default=300, description="DPI resolution for rendering PDF pages to images")
    scanned_text_density_threshold: float = Field(
        default=0.005,
        description="Character count to page area ratio below which a page is treated as scanned",
    )


class AppConfig(BaseModel):
    """Global configuration settings for Document Assistant."""

    app_name: str = "Document Assistant Backend"
    version: str = "0.1.0"
    offline_mode: bool = True
    temp_dir: Path = Field(default_factory=lambda: Path.cwd() / "temp")
    ocr: OCRConfig = Field(default_factory=OCRConfig)
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    pdf: PDFConfig = Field(default_factory=PDFConfig)

    def ensure_temp_dir(self) -> Path:
        """Ensures the temporary workspace directory exists."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        return self.temp_dir


# Global default configuration instance
config = AppConfig()
