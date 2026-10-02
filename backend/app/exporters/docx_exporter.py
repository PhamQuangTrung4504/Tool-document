"""DOCX document exporter."""

from pathlib import Path
from typing import Union

from app.exporters.base import BaseExporter
from app.models.document import Document
from app.services.docx.docx_service import DOCXService


class DOCXExporter(BaseExporter):
    """Exports Document model to Microsoft Word DOCX format."""

    def __init__(self) -> None:
        self.service = DOCXService()

    @property
    def target_format(self) -> str:
        return "docx"

    def export(self, document: Document, output_path: Union[str, Path]) -> Path:
        return self.service.export_to_docx(document, output_path)
