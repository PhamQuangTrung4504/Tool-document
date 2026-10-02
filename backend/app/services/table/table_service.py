"""Table service coordinating table detection and robust fallback to TextElements."""

from typing import List, Optional, Set, Tuple
import numpy as np

from app.core.logging import logger
from app.models.document import Page
from app.models.elements import TableElement, TextElement
from app.services.table.base import TableStructureProvider
from app.services.table.paddle_table_provider import PaddleTableStructureProvider


class TableService:
    """Orchestrates table detection and structure recognition with strict zero-content-loss fallback."""

    def __init__(self, provider: Optional[TableStructureProvider] = None) -> None:
        if provider:
            self.provider = provider
        else:
            self.provider = self._resolve_default_provider()

    @staticmethod
    def _resolve_default_provider() -> TableStructureProvider:
        paddle_provider = PaddleTableStructureProvider()
        return paddle_provider

    def detect_tables(
        self,
        image: np.ndarray,
        ocr_elements: Optional[List[TextElement]] = None,
        confidence_threshold: float = 0.6,
    ) -> Tuple[List[TableElement], List[TextElement]]:
        """Extracts structured tables while preserving all non-table text elements.

        Phase 10 Fallback Guarantee:
        If table recognition fails, encounters an exception, or detects no tables,
        ALL ocr_elements are preserved as regular TextElements. Zero content loss.

        Returns:
            Tuple of (detected_tables, remaining_standalone_text_elements).
        """
        all_elements = list(ocr_elements) if ocr_elements else []

        if not self.provider.is_available():
            logger.debug(f"Table provider '{self.provider.name}' not available; falling back to TextElements")
            return [], all_elements

        try:
            tables = self.provider.detect_tables(
                image=image,
                ocr_elements=all_elements,
                confidence_threshold=confidence_threshold,
            )
        except Exception as e:
            logger.warning(f"Table detection failed with exception: {e}; falling back to TextElements")
            return [], all_elements

        if not tables:
            return [], all_elements

        # Identify which text elements were absorbed into table cells
        absorbed_ids: Set[int] = set()
        for table in tables:
            for cell in table.cells:
                for t in cell.elements:
                    absorbed_ids.add(id(t))

        # Remaining elements are those outside any recognized table
        remaining_elements = [el for el in all_elements if id(el) not in absorbed_ids]
        logger.info(
            f"Detected {len(tables)} table(s). Absorbed {len(absorbed_ids)} text elements; "
            f"{len(remaining_elements)} text elements remain as body text."
        )
        return tables, remaining_elements

    def process_page(
        self,
        page: Page,
        image: np.ndarray,
        confidence_threshold: float = 0.6,
    ) -> Page:
        """Processes a Page, converting text elements inside detected tables into TableElements."""
        text_elements = [el for el in page.elements if isinstance(el, TextElement)]
        other_elements = [el for el in page.elements if not isinstance(el, TextElement)]

        tables, remaining_texts = self.detect_tables(
            image=image,
            ocr_elements=text_elements,
            confidence_threshold=confidence_threshold,
        )

        # Reassemble page elements
        page.elements = tables + remaining_texts + other_elements
        return page
