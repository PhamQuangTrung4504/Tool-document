"""Markdown document exporter."""

from pathlib import Path
from typing import Union

from app.exporters.base import BaseExporter
from app.models.document import Document
from app.models.elements import ImageElement, TableElement, TextElement


class MarkdownExporter(BaseExporter):
    """Exports Document model to structured Markdown with headings, tables, and formatting."""

    @property
    def target_format(self) -> str:
        return "md"

    def export(self, document: Document, output_path: Union[str, Path]) -> Path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        if document.metadata.title:
            lines.append(f"# {document.metadata.title}\n")

        for page_idx, page in enumerate(document.pages):
            if page_idx > 0:
                lines.append("\n---\n")

            sorted_elements = page.get_sorted_elements()
            for el in sorted_elements:
                if isinstance(el, TextElement):
                    text = el.text.strip()
                    if not text:
                        continue

                    # Apply bold/italic markdown syntax
                    if el.bold and el.italic:
                        text = f"***{text}***"
                    elif el.bold:
                        text = f"**{text}**"
                    elif el.italic:
                        text = f"*{text}*"

                    if el.is_heading():
                        lines.append(f"## {text}\n")
                    else:
                        lines.append(f"{text}\n")

                elif isinstance(el, TableElement):
                    md_table = el.to_markdown()
                    if md_table:
                        lines.append(f"\n{md_table}\n")

                elif isinstance(el, ImageElement):
                    caption = el.description or "Image"
                    if el.image_path:
                        lines.append(f"![{caption}]({el.image_path.name})\n")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return out_path
