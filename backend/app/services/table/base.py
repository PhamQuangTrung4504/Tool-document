"""Abstract base class and contract for Table Structure Recognition Providers."""

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from app.models.elements import TableElement, TextElement


class TableStructureProvider(ABC):
    """Abstract interface for Table Structure Recognition engines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the table structure provider."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Checks whether the table engine dependencies/models are available."""
        pass

    @abstractmethod
    def detect_tables(
        self,
        image: np.ndarray,
        ocr_elements: Optional[List[TextElement]] = None,
        confidence_threshold: float = 0.5,
    ) -> List[TableElement]:
        """Detects tables and parses structural cell grids from an image.

        Args:
            image: Image as numpy array (BGR or RGB).
            ocr_elements: Optional OCR text elements already recognized on this image.
            confidence_threshold: Minimum structure score to accept table.

        Returns:
            List of structured TableElements.
        """
        pass
