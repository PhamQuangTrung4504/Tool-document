"""Exporters package exporting factory and implementations."""

from typing import Dict, Optional, Type
from app.core.exceptions import UnsupportedFormatError
from app.exporters.base import BaseExporter
from app.exporters.docx_exporter import DOCXExporter
from app.exporters.html_exporter import HTMLExporter
from app.exporters.markdown_exporter import MarkdownExporter
from app.exporters.pdf_exporter import PDFExporter
from app.exporters.txt_exporter import TXTExporter

EXPORTERS: Dict[str, Type[BaseExporter]] = {
    "txt": TXTExporter,
    "text": TXTExporter,
    "docx": DOCXExporter,
    "pdf": PDFExporter,
    "html": HTMLExporter,
    "htm": HTMLExporter,
    "md": MarkdownExporter,
    "markdown": MarkdownExporter,
}


def get_exporter(format_name: str) -> BaseExporter:
    """Returns an exporter instance for the target format."""
    normalized = format_name.lower().lstrip(".")
    if normalized not in EXPORTERS:
        raise UnsupportedFormatError(
            normalized,
            f"Exporting to format '{normalized}' is not supported. Supported: {list(set(EXPORTERS.keys()))}",
        )
    return EXPORTERS[normalized]()


__all__ = [
    "BaseExporter",
    "TXTExporter",
    "DOCXExporter",
    "PDFExporter",
    "HTMLExporter",
    "MarkdownExporter",
    "get_exporter",
    "EXPORTERS",
]
