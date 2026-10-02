"""Unified OCR Service orchestrating image preprocessing and OCR recognition.

Produces standardized Document Model objects (Page, Document, TextElement) with
exact spatial coordinates and confidence values.
"""

import inspect
from pathlib import Path
from typing import List, Optional, Union
import numpy as np
from PIL import Image

from app.config import config
from app.core.exceptions import OCRProcessingError
from app.core.logging import logger
from app.models.document import Document, DocumentMetadata, Page
from app.models.elements import TextElement
from app.models.enums import OCRMode
from app.services.image.preprocessor import ImagePreprocessor
from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.paddle_provider import PaddleOCRProvider
from app.services.ocr.tesseract_provider import TesseractOCRProvider


class OCRService:
    """High-level service coordinating OCR extraction pipelines."""

    def __init__(self, provider: Optional[BaseOCRProvider] = None) -> None:
        if provider:
            self.provider = provider
        else:
            self.provider = self._resolve_default_provider()

    @staticmethod
    def _resolve_default_provider() -> BaseOCRProvider:
        """Determines the best available OCR engine: PaddleOCR -> Tesseract."""
        paddle = PaddleOCRProvider(
            default_lang=config.ocr.default_language,
            use_angle_cls=config.ocr.use_angle_cls,
            gpu=config.ocr.enable_gpu,
        )
        if paddle.is_available():
            return paddle

        tesseract = TesseractOCRProvider(default_lang="vie+eng")
        if tesseract.is_available():
            return tesseract

        # Return paddle provider by default even if dependencies are missing yet,
        # so clear error message is raised when invoked.
        return paddle

    def _resolve_auto_mode(self, image: np.ndarray) -> OCRMode:
        """Heuristically decides between FAST and FULL OCR modes based on image degradation.

        Rules:
        - Significant tilt (|skew| > 2.5°) -> FULL
        - Low contrast (std < 35.0) -> FULL
        - Blurry scan (Laplacian var < 80.0) -> FULL
        - Otherwise (straight, clear) -> FAST
        """
        try:
            import cv2
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

            skew = ImagePreprocessor.detect_skew_angle(gray)
            if abs(skew) > 2.5:
                logger.debug(f"AUTO OCR mode selected FULL: significant skew detected ({skew:.2f}°)")
                return OCRMode.FULL

            contrast_std = float(gray.std())
            if contrast_std < 35.0:
                logger.debug(f"AUTO OCR mode selected FULL: low contrast detected (std={contrast_std:.1f})")
                return OCRMode.FULL

            lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if lap_var < 80.0:
                logger.debug(f"AUTO OCR mode selected FULL: blurry scan detected (lap_var={lap_var:.1f})")
                return OCRMode.FULL

            logger.debug("AUTO OCR mode selected FAST: image is straight and high quality")
            return OCRMode.FAST
        except Exception as e:
            logger.warning(f"AUTO mode heuristic encountered error, defaulting to FAST: {e}")
            return OCRMode.FAST

    def recognize_image(
        self,
        source: Union[str, Path, bytes, np.ndarray, Image.Image],
        mode: Union[OCRMode, str] = OCRMode.FAST,
        preprocess: bool = True,
        deskew: bool = True,
        denoise: bool = True,
        enhance: bool = True,
        lang: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
    ) -> List[TextElement]:
        """Runs the complete OCR pipeline: load -> preprocess -> OCR -> TextElements.

        Args:
            source: Image input (path, bytes, ndarray, or PIL Image).
            mode: OCRMode (FAST, FULL, or AUTO). Defaults to FAST.
            preprocess: Whether to run preprocessing pipeline.
            deskew: Whether to auto-correct skew tilt.
            denoise: Whether to filter noise.
            enhance: Whether to enhance contrast with CLAHE.
            lang: Target language code ('vi', 'en', etc.).
            confidence_threshold: Minimum confidence filter.

        Returns:
            List of TextElements with bounding box and confidence score.
        """
        conf_thresh = confidence_threshold or config.ocr.confidence_threshold
        target_lang = lang or config.ocr.default_language

        raw_array = ImagePreprocessor.load_image(source)

        # Resolve mode
        selected_mode = OCRMode(mode) if isinstance(mode, str) else mode
        if selected_mode == OCRMode.AUTO:
            effective_mode = self._resolve_auto_mode(raw_array)
        else:
            effective_mode = selected_mode

        if preprocess:
            image_array = ImagePreprocessor.process(
                raw_array,
                deskew=deskew,
                denoise=denoise,
                enhance=enhance,
                threshold=False,
                cleanup_border=False,
            )
        else:
            image_array = raw_array

        # Maintain 100% backward compatibility with legacy providers or test mocks
        sig = inspect.signature(self.provider.recognize)
        call_kwargs = {
            "image": image_array,
            "lang": target_lang,
            "confidence_threshold": conf_thresh,
        }
        if "mode" in sig.parameters or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            call_kwargs["mode"] = effective_mode

        return self.provider.recognize(**call_kwargs)

    def process(
        self,
        source: Union[str, Path, bytes, np.ndarray, Image.Image],
        mode: Union[OCRMode, str] = OCRMode.FAST,
        **kwargs,
    ) -> List[TextElement]:
        """Standardized interface executing OCR in FAST, FULL, or AUTO mode."""
        return self.recognize_image(source=source, mode=mode, **kwargs)

    def image_to_page(
        self,
        source: Union[str, Path, bytes, np.ndarray, Image.Image],
        page_number: int = 1,
        mode: Union[OCRMode, str] = OCRMode.FAST,
        preprocess: bool = True,
        deskew: bool = True,
        denoise: bool = True,
        enhance: bool = True,
        lang: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
    ) -> Page:
        """Converts an image into a standardized Document Page object with extracted text elements."""
        img_array = ImagePreprocessor.load_image(source)
        h, w = img_array.shape[:2]

        elements = self.recognize_image(
            source=img_array,
            mode=mode,
            preprocess=preprocess,
            deskew=deskew,
            denoise=denoise,
            enhance=enhance,
            lang=lang,
            confidence_threshold=confidence_threshold,
        )

        page = Page(
            page_number=page_number,
            width=float(w),
            height=float(h),
            elements=elements,
        )
        return page

    def image_to_document(
        self,
        source: Union[str, Path, bytes, np.ndarray, Image.Image],
        mode: Union[OCRMode, str] = OCRMode.FAST,
        title: Optional[str] = None,
        lang: Optional[str] = None,
    ) -> Document:
        """Converts a single image directly into a Document model."""
        source_name = str(source) if isinstance(source, (str, Path)) else "image"
        doc = Document(
            metadata=DocumentMetadata(
                title=title or Path(source_name).stem,
                source_path=str(source) if isinstance(source, (str, Path)) else None,
                source_format="image",
                page_count=1,
            )
        )
        page = self.image_to_page(source=source, page_number=1, mode=mode, lang=lang)
        doc.add_page(page)
        return doc


def get_ocr_service(provider_name: Optional[str] = None) -> OCRService:
    """Factory function for OCRService."""
    if provider_name == "tesseract":
        return OCRService(provider=TesseractOCRProvider())
    elif provider_name == "paddle":
        return OCRService(provider=PaddleOCRProvider())
    return OCRService()
