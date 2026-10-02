"""PaddleOCR Provider implementation with Vietnamese and multi-language support."""

import inspect
from typing import Any, Dict, List, Optional
import numpy as np

from app.core.exceptions import OCRProcessingError
from app.core.logging import logger
from app.models.elements import TextElement
from app.models.enums import OCRMode
from app.models.geometry import BoundingBox
from app.services.ocr.base import BaseOCRProvider


def _apply_paddlex_windows_cpu_patch() -> None:
    """Applies compatibility patch for PaddlePaddle 3.x / PaddleX on Windows CPU.

    Disables oneDNN PIR new_ir instruction conversion that causes
    'ConvertPirAttribute2RuntimeAttribute not support' error on Windows CPU.
    """
    try:
        from paddlex.inference.models.runners.paddle_static.runner import PaddleStaticRunner
        import paddlex.inference.models.runners.paddle_static.runner as runner_module

        if getattr(PaddleStaticRunner, "_windows_patched", False):
            return

        orig_create = PaddleStaticRunner._create

        def safe_create(self: Any) -> Any:
            try:
                p_inf = runner_module.import_paddle_module("paddle.inference")
                model_paths = runner_module.get_model_paths(self.model_dir, self.model_file_prefix)
                model_file, params_file = model_paths["paddle"]

                config = p_inf.Config(str(model_file), str(params_file))
                config.disable_gpu()
                if hasattr(config, "disable_mkldnn"):
                    config.disable_mkldnn()
                if hasattr(config, "enable_new_ir"):
                    config.enable_new_ir(False)
                config.set_cpu_math_library_num_threads(4)
                config.disable_glog_info()

                return p_inf.create_predictor(config)
            except Exception:
                return orig_create(self)

        PaddleStaticRunner._create = safe_create
        PaddleStaticRunner._windows_patched = True
    except Exception:
        pass


class PaddleOCRProvider(BaseOCRProvider):
    """PaddleOCR integration supporting high-accuracy Vietnamese recognition and orientation detection."""

    def __init__(self, default_lang: str = "vi", use_angle_cls: bool = True, gpu: bool = False) -> None:
        self.default_lang = default_lang
        self.use_angle_cls = use_angle_cls
        self.gpu = gpu
        self._instances: Dict[Any, Any] = {}

    @property
    def name(self) -> str:
        return "PaddleOCR"

    def is_available(self) -> bool:
        """Checks if paddleocr and paddlepaddle are available in current Python environment."""
        try:
            import paddleocr  # noqa: F401
            import paddle  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_ocr_instance(self, lang: str, mode: OCRMode = OCRMode.FAST) -> Any:
        """Lazily initializes and caches the PaddleOCR engine per language and mode."""
        mode_val = mode.value if isinstance(mode, OCRMode) else str(mode)
        cache_key = (lang, mode_val)
        if cache_key in self._instances:
            return self._instances[cache_key]

        try:
            _apply_paddlex_windows_cpu_patch()
            from paddleocr import PaddleOCR

            sig = inspect.signature(PaddleOCR.__init__)
            params = sig.parameters

            init_kwargs: Dict[str, Any] = {"lang": lang}

            # Phase 7: FAST vs FULL mode control
            if mode == OCRMode.FULL:
                if "use_doc_orientation_classify" in params:
                    init_kwargs["use_doc_orientation_classify"] = True
                if "use_doc_unwarping" in params:
                    init_kwargs["use_doc_unwarping"] = True
                if "use_textline_orientation" in params:
                    init_kwargs["use_textline_orientation"] = True
                elif "use_angle_cls" in params:
                    init_kwargs["use_angle_cls"] = True
            else:
                # FAST: disable heavy orientation & unwarping models
                if "use_doc_orientation_classify" in params:
                    init_kwargs["use_doc_orientation_classify"] = False
                if "use_doc_unwarping" in params:
                    init_kwargs["use_doc_unwarping"] = False
                if "use_textline_orientation" in params:
                    init_kwargs["use_textline_orientation"] = False
                elif "use_angle_cls" in params:
                    init_kwargs["use_angle_cls"] = False

            if "use_gpu" in params:
                init_kwargs["use_gpu"] = self.gpu

            if "show_log" in params:
                init_kwargs["show_log"] = False

            instance = PaddleOCR(**init_kwargs)
            self._instances[cache_key] = instance
            return instance
        except Exception as e:
            raise OCRProcessingError(
                f"Failed to initialize PaddleOCR engine for language '{lang}' in {mode_val} mode: {e}",
                provider=self.name,
            )

    def recognize(
        self,
        image: np.ndarray,
        lang: Optional[str] = None,
        confidence_threshold: float = 0.5,
        mode: OCRMode = OCRMode.FAST,
    ) -> List[TextElement]:
        """Runs PaddleOCR on the image and converts raw detections into TextElements."""
        target_lang = lang or self.default_lang
        ocr_engine = self._get_ocr_instance(target_lang, mode=mode)

        raw_results = None
        try:
            # PaddleOCR 3.x recommends predict(), while 2.x uses ocr()
            if hasattr(ocr_engine, "predict"):
                raw_results = ocr_engine.predict(image)
            else:
                raw_results = ocr_engine.ocr(image, cls=self.use_angle_cls)
        except Exception as e:
            # Fallback to ocr() if predict failed
            try:
                raw_results = ocr_engine.ocr(image)
            except Exception as ex:
                raise OCRProcessingError(f"PaddleOCR recognition failed: {e} / {ex}", provider=self.name)

        elements: List[TextElement] = []
        if not raw_results:
            return elements

        # Handle PaddleOCR 3.x structure: list of dicts with rec_texts, rec_scores, dt_polys
        for item in raw_results:
            if isinstance(item, dict):
                texts = item.get("rec_texts", [])
                scores = item.get("rec_scores", [])
                polys = item.get("dt_polys", item.get("rec_polys", []))

                for text, score, poly in zip(texts, scores, polys):
                    text_str = str(text).strip()
                    conf = float(score)
                    if conf < confidence_threshold or not text_str:
                        continue

                    # Poly can be list or np.ndarray of 4 points [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                    points = poly.tolist() if isinstance(poly, np.ndarray) else poly
                    bbox = BoundingBox.from_points(points)
                    elements.append(
                        TextElement(
                            text=text_str,
                            bbox=bbox,
                            confidence=conf,
                            font_size=max(8.0, bbox.height * 0.75),
                        )
                    )
            elif isinstance(item, (list, tuple)):
                # Handle PaddleOCR 2.x structure: [[[x1,y1],...], (text, score)]
                for line in item:
                    try:
                        points = line[0]
                        text_info = line[1]
                        text = str(text_info[0]).strip()
                        confidence = float(text_info[1])

                        if confidence < confidence_threshold or not text:
                            continue

                        bbox = BoundingBox.from_points(points)
                        elements.append(
                            TextElement(
                                text=text,
                                bbox=bbox,
                                confidence=confidence,
                                font_size=max(8.0, bbox.height * 0.75),
                            )
                        )
                    except Exception as ex:
                        logger.debug(f"Skipping malformed OCR line: {ex}")
                        continue

        return elements
