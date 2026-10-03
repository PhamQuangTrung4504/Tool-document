"""HTML document exporter."""

import html
from pathlib import Path
from typing import Union

from app.exporters.base import BaseExporter
from app.models.document import Document
from app.models.elements import ImageElement, TableElement, TextAlignment, TextElement


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

                elif isinstance(el, ImageElement):
                    import base64
                    img_data = el.image_data
                    if not img_data and el.image_path and Path(el.image_path).exists():
                        try:
                            img_data = Path(el.image_path).read_bytes()
                        except Exception:
                            img_data = None

                    if img_data:
                        fmt = el.format or "png"
                        b64_str = base64.b64encode(img_data).decode("ascii")
                        data_uri = f"data:image/{fmt};base64,{b64_str}"
                        w_pt = el.bbox.width if el.bbox.width > 20 else 200.0
                        body_parts.append(
                            f'<div class="doc-image" style="margin: 12px 0;">'
                            f'<img src="{data_uri}" style="max-width: 100%; width: {w_pt:.1f}pt; height: auto; display: block;" alt="Document Image" />'
                            f'</div>'
                        )

                elif isinstance(el, TableElement):
                    if el.rows > 0 and el.columns > 0:
                        body_parts.append('<table class="doc-table">')
                        covered = [[False for _ in range(el.columns)] for _ in range(el.rows)]

                        # Map cell positions
                        cell_map = {(c.row_index, c.col_index): c for c in el.cells}

                        for r in range(el.rows):
                            body_parts.append("<tr>")
                            for c in range(el.columns):
                                if covered[r][c]:
                                    continue

                                cell = cell_map.get((r, c))
                                if cell is None:
                                    tag = "th" if (r < el.header_rows and el.has_header) else "td"
                                    body_parts.append(f"<{tag}></{tag}>")
                                    covered[r][c] = True
                                    continue

                                r_span = max(1, cell.row_span)
                                c_span = max(1, cell.col_span)

                                for dr in range(r_span):
                                    for dc in range(c_span):
                                        if r + dr < el.rows and c + dc < el.columns:
                                            covered[r + dr][c + dc] = True

                                span_attrs = []
                                if r_span > 1:
                                    span_attrs.append(f'rowspan="{r_span}"')
                                if c_span > 1:
                                    span_attrs.append(f'colspan="{c_span}"')
                                span_str = f" {' '.join(span_attrs)}" if span_attrs else ""

                                tag = "th" if (r < el.header_rows and el.has_header) else "td"
                                escaped_val = html.escape(cell.text).replace("\n", "<br/>")
                                body_parts.append(f"<{tag}{span_str}>{escaped_val}</{tag}>")
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
