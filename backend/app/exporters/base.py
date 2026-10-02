"""Abstract base class and contract for document exporters.

Decouples document serialization from OCR and parsing logic:
Document Model -> Exporter -> Output File.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from app.models.document import Document


class BaseExporter(ABC):
    """Abstract interface for all document exporters."""

    @property
    @abstractmethod
    def target_format(self) -> str:
        """Name or extension of the target format (e.g. 'txt', 'docx', 'pdf', 'html')."""
        pass

    @abstractmethod
    def export(self, document: Document, output_path: Union[str, Path]) -> Path:
        """Serializes the intermediate Document model to the specified destination path.

        Args:
            document: Document model instance.
            output_path: Target output file path.

        Returns:
            Resolved Path of the written file.
        """
        pass
