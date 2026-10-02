"""HTML document exporter."""

import html
from pathlib import Path
from typing import Union

from app.exporters.base import BaseExporter
from app.models.document import Document
from app.models.elements import TableElement, TextAlignment, TextElement


class HTMLExporter(BaseExporter):
    """Exports Document model to styled, standalone HTML5 document."""

    @property
    def target_format(self) -> str:
        return "html"

    def export(self, document: Document, output_path: Union[str, Path]) -> Path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        title = html.escape(document.metadata.title or "Document")
        body_parts = []

        for page in document.pages:
            body_parts.append('<div class="document-page">')
            sorted_elements = page.get_sorted_elements()

            for el in sorted_elements:
                if isinstance(el, TextElement):
                    escaped_text = html.escape(el.text)
                    style_chunks = []
                    if el.bold:
                        style_chunks.append("font-weight: bold;")
                    if el.italic:
                        style_chunks.append("font-style: italic;")
                    if el.underline:
                        style_chunks.append("text-decoration: underline;")
                    if el.alignment != TextAlignment.LEFT:
                        style_chunks.append(f"text-align: {el.alignment.value};")
                    if el.color and el.color != "#000000":
                        style_chunks.append(f"color: {el.color};")
                    if el.font_size:
                        style_chunks.append(f"font-size: {el.font_size}pt;")

                    style_attr = f' style="{" ".join(style_chunks)}"' if style_chunks else ""

                    if el.is_heading():
                        body_parts.append(f"<h2{style_attr}>{escaped_text}</h2>")
                    else:
                        body_parts.append(f"<p{style_attr}>{escaped_text}</p>")

                elif isinstance(el, TableElement):
                    matrix = el.to_matrix()
                    if matrix:
                        body_parts.append('<table class="doc-table">')
                        for r_idx, row in enumerate(matrix):
                            tag = "th" if (r_idx == 0 and el.has_header) else "td"
                            body_parts.append("<tr>")
                            for val in row:
                                body_parts.append(f"<{tag}>{html.escape(val)}</{tag}>")
                            body_parts.append("</tr>")
                        body_parts.append("</table>")

            body_parts.append("</div>")

        html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f3f4f6;
            margin: 0;
            padding: 20px;
            color: #1f2937;
        }}
        .document-page {{
            background: #ffffff;
            max-width: 800px;
            margin: 20px auto;
            padding: 40px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            border-radius: 4px;
            min-height: 800px;
        }}
        p {{
            margin: 0 0 10px 0;
            line-height: 1.5;
        }}
        h2 {{
            margin: 20px 0 10px 0;
            color: #111827;
        }}
        .doc-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        .doc-table th, .doc-table td {{
            border: 1px solid #d1d5db;
            padding: 8px 12px;
            text-align: left;
        }}
        .doc-table th {{
            background-color: #f9fafb;
            font-weight: 600;
        }}
    </style>
</head>
<body>
{"\n".join(body_parts)}
</body>
</html>
"""
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return out_path
