"""Document Fidelity Service computing objective metrics between source and converted documents."""

from typing import List, Optional
from app.models.document import Document
from app.models.elements import ImageElement, TableElement, TextElement
from app.models.fidelity import DocumentFidelityReport


class DocumentFidelityService:
    """Computes comprehensive, objective fidelity metrics without subjective quality scoring."""

    @staticmethod
    def evaluate(
        source_doc: Document,
        target_doc: Optional[Document] = None,
        target_text: Optional[str] = None,
    ) -> DocumentFidelityReport:
        """Evaluates source Document model and compares with output Document or extracted text."""
        warnings: List[str] = []

        source_pages = len(source_doc.pages)
        source_chars = sum(len(p.get_text()) for p in source_doc.pages)

        # Count elements, tables, images, and confidence
        total_elements = 0
        total_tables = 0
        total_images = 0
        conf_scores: List[float] = []
        total_page_area = 0.0
        total_bbox_area = 0.0

        for page in source_doc.pages:
            page_area = page.width * page.height
            total_page_area += page_area

            for el in page.elements:
                total_elements += 1
                total_bbox_area += el.bbox.area

                if isinstance(el, TextElement):
                    conf_scores.append(el.confidence)
                elif isinstance(el, TableElement):
                    total_tables += 1
                    conf_scores.append(el.confidence)
                elif isinstance(el, ImageElement):
                    total_images += 1

        avg_confidence = float(sum(conf_scores) / max(1, len(conf_scores))) if conf_scores else 1.0

        # Calculate bounding box area coverage
        bbox_coverage = min(1.0, float(total_bbox_area / max(1.0, total_page_area)))

        # Output text and page metrics
        if target_doc is not None:
            output_pages = len(target_doc.pages)
            output_chars = sum(len(p.get_text()) for p in target_doc.pages)
        elif target_text is not None:
            output_pages = source_pages
            output_chars = len(target_text)
        else:
            output_pages = source_pages
            output_chars = source_chars

        if source_chars > 0:
            text_coverage = min(2.0, float(output_chars / source_chars))
        else:
            text_coverage = 1.0 if output_chars == 0 else 0.0

        # Objective diagnostic checks
        if source_pages != output_pages:
            warnings.append(f"Page count mismatch: source has {source_pages} pages, output has {output_pages} pages.")

        if source_chars > 50 and output_chars < source_chars * 0.5:
            warnings.append("Significant text loss detected: output contains less than 50% of source characters.")

        if avg_confidence < 0.70:
            warnings.append(f"Low average recognition confidence: {avg_confidence:.2%}.")

        if source_chars == 0:
            warnings.append("Source document text is empty (no text extracted or recognized).")

        return DocumentFidelityReport(
            source_pages=source_pages,
            output_pages=output_pages,
            source_text_chars=source_chars,
            output_text_chars=output_chars,
            text_coverage=text_coverage,
            ocr_confidence_avg=avg_confidence,
            tables_detected=total_tables,
            images_detected=total_images,
            element_count=total_elements,
            bounding_box_coverage=bbox_coverage,
            warnings=warnings,
        )
