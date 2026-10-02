"""Plain text exporter."""

from pathlib import Path
from typing import Union

from app.exporters.base import BaseExporter
from app.models.document import Document


class TXTExporter(BaseExporter):
    """Exports Document model to UTF-8 plain text."""

    @property
    def target_format(self) -> str:
        return "txt"

    def export(self, document: Document, output_path: Union[str, Path]) -> Path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        full_text = document.get_full_text(page_separator="\n\n" + "=" * 40 + "\n\n")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_text)

        return out_path
