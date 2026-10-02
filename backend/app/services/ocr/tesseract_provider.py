"""Tesseract OCR Provider fallback implementation."""

from typing import Dict, List, Optional
import numpy as np

from app.core.exceptions import OCRProcessingError
from app.core.logging import logger
from app.models.elements import TextElement
from app.models.enums import OCRMode
from app.models.geometry import BoundingBox
from app.services.ocr.base import BaseOCRProvider


class TesseractOCRProvider(BaseOCRProvider):
    """Tesseract OCR engine integration using pytesseract."""

    def __init__(self, default_lang: str = "vie+eng") -> None:
        self.default_lang = default_lang

    @property
    def name(self) -> str:
        return "Tesseract"

    def is_available(self) -> bool:
        """Checks if pytesseract and tesseract executable are available."""
        try:
            import pytesseract
            # Test getting tesseract version
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def recognize(
        self,
        image: np.ndarray,
        lang: Optional[str] = None,
        confidence_threshold: float = 0.5,
        mode: OCRMode = OCRMode.FAST,
    ) -> List[TextElement]:
        """Runs Tesseract OCR and groups recognized words into line-level TextElements."""
        try:
            import pytesseract
            from pytesseract import Output
        except ImportError:
            raise OCRProcessingError("pytesseract package is not installed", provider=self.name)

        target_lang = lang or self.default_lang
        # Map simple codes to tesseract lang codes
        if target_lang == "vi":
            target_lang = "vie"
        elif target_lang == "en":
            target_lang = "eng"

        try:
            data = pytesseract.image_to_data(image, lang=target_lang, output_type=Output.DICT)
        except Exception as e:
            raise OCRProcessingError(f"Tesseract OCR failed: {e}", provider=self.name)

        n_boxes = len(data["text"])
        line_groups: Dict[tuple, List[dict]] = {}

        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf_str = data["conf"][i]
            try:
                conf = float(conf_str) / 100.0
            except (ValueError, TypeError):
                conf = 0.0

            if not text or conf < confidence_threshold:
                continue

            key = (data["page_num"][i], data["block_num"][i], data["par_num"][i], data["line_num"][i])
            word_info = {
                "text": text,
                "x1": float(data["left"][i]),
                "y1": float(data["top"][i]),
                "x2": float(data["left"][i] + data["width"][i]),
                "y2": float(data["top"][i] + data["height"][i]),
                "conf": conf,
            }
            line_groups.setdefault(key, []).append(word_info)

        elements: List[TextElement] = []
        for line_words in line_groups.values():
            line_text = " ".join(w["text"] for w in line_words)
            x1 = min(w["x1"] for w in line_words)
            y1 = min(w["y1"] for w in line_words)
            x2 = max(w["x2"] for w in line_words)
            y2 = max(w["y2"] for w in line_words)
            avg_conf = sum(w["conf"] for w in line_words) / len(line_words)
            bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)

            elements.append(
                TextElement(
                    text=line_text,
                    bbox=bbox,
                    confidence=avg_conf,
                    font_size=max(8.0, bbox.height * 0.75),
                )
            )

        return elements
