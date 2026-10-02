"""PaddleOCR Table Structure Recognition Provider using SLANet."""

import re
from typing import Any, List, Optional
import numpy as np

from app.core.logging import logger
from app.models.elements import TableCell, TableElement, TextElement
from app.models.geometry import BoundingBox
from app.services.ocr.paddle_provider import _apply_paddlex_windows_cpu_patch
from app.services.table.base import TableStructureProvider


class PaddleTableStructureProvider(TableStructureProvider):
    """Integrates SLANet table structure recognition model from PaddleOCR."""

    def __init__(self) -> None:
        self._engine: Optional[Any] = None

    @property
    def name(self) -> str:
        return "PaddleSLANet"

    def is_available(self) -> bool:
        """Checks if TableStructureRecognition can be imported from paddleocr."""
        try:
            from paddleocr import TableStructureRecognition  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_engine(self) -> Any:
        """Lazily initializes and caches TableStructureRecognition engine."""
        if self._engine is not None:
            return self._engine

        _apply_paddlex_windows_cpu_patch()
        from paddleocr import TableStructureRecognition

        self._engine = TableStructureRecognition()
        return self._engine

    def detect_tables(
        self,
        image: np.ndarray,
        ocr_elements: Optional[List[TextElement]] = None,
        confidence_threshold: float = 0.6,
    ) -> List[TableElement]:
        """Runs SLANet on image to extract table grid and coordinates."""
        try:
            engine = self._get_engine()
            results = engine.predict(image)
        except Exception as e:
            logger.warning(f"PaddleTableStructureProvider failed during inference: {e}")
            return []

        if not results:
            return []

        tables: List[TableElement] = []

        for item in results:
            if not isinstance(item, dict):
                continue

            structure = item.get("structure", [])
            raw_bboxes = item.get("bbox", [])
            structure_score = float(item.get("structure_score", 0.0))

            if structure_score < confidence_threshold or not structure or not raw_bboxes:
                continue

            # Parse HTML structure tokens and match with cell bboxes
            cells: List[TableCell] = []
            row_idx = -1
            col_idx = 0
            bbox_idx = 0
            max_cols = 0

            for token in structure:
                if token == "<tr>":
                    row_idx += 1
                    col_idx = 0
                elif token.startswith("<td"):
                    # Check for rowspan and colspan
                    r_match = re.search(r'rowspan="(\d+)"', token)
                    c_match = re.search(r'colspan="(\d+)"', token)
                    rowspan = int(r_match.group(1)) if r_match else 1
                    colspan = int(c_match.group(1)) if c_match else 1

                    cell_bbox: Optional[BoundingBox] = None
                    if bbox_idx < len(raw_bboxes):
                        b = raw_bboxes[bbox_idx]
                        bbox_idx += 1
                        if len(b) == 8:
                            cell_bbox = BoundingBox(
                                x1=float(min(b[0], b[6])),
                                y1=float(min(b[1], b[3])),
                                x2=float(max(b[2], b[4])),
                                y2=float(max(b[5], b[7])),
                            )
                        elif len(b) >= 4:
                            cell_bbox = BoundingBox(
                                x1=float(b[0]),
                                y1=float(b[1]),
                                x2=float(b[2]),
                                y2=float(b[3]),
                            )

                    cell = TableCell(
                        row_index=row_idx,
                        col_index=col_idx,
                        row_span=rowspan,
                        col_span=colspan,
                        bbox=cell_bbox,
                        confidence=structure_score,
                    )
                    cells.append(cell)
                    col_idx += colspan
                    if col_idx > max_cols:
                        max_cols = col_idx

            if not cells or row_idx < 0:
                continue

            total_rows = row_idx + 1
            total_cols = max(1, max_cols)

            # Match cell bounding boxes with OCR text elements
            if ocr_elements:
                for cell in cells:
                    if not cell.bbox:
                        continue
                    matched: List[TextElement] = []
                    for t_el in ocr_elements:
                        # Spatial containment: center point falls inside cell bbox
                        if (
                            cell.bbox.x1 - 2.0 <= t_el.bbox.center_x <= cell.bbox.x2 + 2.0
                            and cell.bbox.y1 - 2.0 <= t_el.bbox.center_y <= cell.bbox.y2 + 2.0
                        ):
                            matched.append(t_el)

                    if matched:
                        # Sort natural order within cell
                        matched.sort(key=lambda t: (round(t.bbox.y1 / 4.0) * 4.0, t.bbox.x1))
                        cell.elements = matched
                        cell.text = " ".join(t.text for t in matched)

            # Calculate total table bounding box
            cell_boxes = [c.bbox for c in cells if c.bbox]
            if cell_boxes:
                table_bbox = BoundingBox(
                    x1=min(c.x1 for c in cell_boxes),
                    y1=min(c.y1 for c in cell_boxes),
                    x2=max(c.x2 for c in cell_boxes),
                    y2=max(c.y2 for c in cell_boxes),
                )
            else:
                table_bbox = BoundingBox(x1=0.0, y1=0.0, x2=100.0, y2=100.0)

            table_el = TableElement(
                bbox=table_bbox,
                rows=total_rows,
                columns=total_cols,
                cells=cells,
                has_header=True,
                confidence=structure_score,
            )
            tables.append(table_el)

        return tables
