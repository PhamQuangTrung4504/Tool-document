"""Abstract base class and contract for OCR Providers.

Enables seamless swapping between PaddleOCR, Tesseract, Local AI, or Cloud OCR engines
without impacting document parsers or conversion pipelines.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from app.models.elements import TextElement
from app.models.enums import OCRMode


class BaseOCRProvider(ABC):
    """Abstract interface that all OCR engine implementations must adhere to."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the OCR provider (e.g. 'PaddleOCR', 'Tesseract')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if the engine binaries and dependencies are properly installed."""
        pass

    @abstractmethod
    def recognize(
        self,
        image: np.ndarray,
        lang: Optional[str] = None,
        confidence_threshold: float = 0.5,
        mode: OCRMode = OCRMode.FAST,
    ) -> List[TextElement]:
        """Performs optical character recognition on an image array.

        Args:
            image: OpenCV BGR or Grayscale image array.
            lang: Language code (e.g. 'vi', 'en').
            confidence_threshold: Minimum confidence score [0.0 - 1.0].
            mode: Processing mode (FAST, FULL, AUTO).

        Returns:
            List of TextElement instances with bounding boxes and confidence scores.
        """
        pass
