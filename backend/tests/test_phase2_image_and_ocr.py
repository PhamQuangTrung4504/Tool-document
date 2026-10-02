"""Unit tests for Phase 2: Image Preprocessing and OCR Service."""

import numpy as np
import pytest
from PIL import Image

from app.core.exceptions import InvalidDocumentError, OCRProcessingError
from app.models.document import Document, Page
from app.models.elements import TextElement
from app.models.geometry import BoundingBox
from app.services.image.preprocessor import ImagePreprocessor
from app.services.ocr.base import BaseOCRProvider
from app.services.ocr.ocr_service import OCRService


class DummyOCRProvider(BaseOCRProvider):
    """Deterministic dummy provider for testing OCR service contracts."""

    def __init__(self, detected_texts=None):
        self.detected_texts = detected_texts or ["CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", "Độc lập - Tự do - Hạnh phúc"]

    @property
    def name(self) -> str:
        return "DummyOCR"

    def is_available(self) -> bool:
        return True

    def recognize(self, image: np.ndarray, lang=None, confidence_threshold=0.5):
        elements = []
        for i, text in enumerate(self.detected_texts):
            elements.append(
                TextElement(
                    text=text,
                    bbox=BoundingBox(x1=50, y1=50 + i * 30, x2=400, y2=75 + i * 30),
                    confidence=0.95,
                    font_size=12.0,
                )
            )
        return elements


def test_image_preprocessor_load_and_gray():
    """Validates loading from ndarray, PIL image, and grayscale conversion."""
    # Synthetic RGB image 200x300
    rgb_arr = np.ones((200, 300, 3), dtype=np.uint8) * 128
    loaded = ImagePreprocessor.load_image(rgb_arr)
    assert loaded.shape == (200, 300, 3)

    # From PIL
    pil_img = Image.fromarray(rgb_arr)
    loaded_pil = ImagePreprocessor.load_image(pil_img)
    assert loaded_pil.shape == (200, 300, 3)

    # Grayscale
    gray = ImagePreprocessor.to_grayscale(loaded)
    assert len(gray.shape) == 2
    assert gray.shape == (200, 300)


def test_image_preprocessor_resize():
    """Validates image resizing by max dimension and scale factor."""
    img = np.zeros((400, 800, 3), dtype=np.uint8)

    # Resize by max_dim=400 (aspect ratio preserved: 800 -> 400, 400 -> 200)
    resized_max = ImagePreprocessor.resize(img, max_dim=400)
    assert resized_max.shape == (200, 400, 3)

    # Resize by scale 0.5
    resized_scale = ImagePreprocessor.resize(img, scale=0.5)
    assert resized_scale.shape == (200, 400, 3)


def test_image_preprocessor_filters():
    """Validates contrast enhancement, denoising, and thresholding."""
    # Create image with gradients and noise
    img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

    enhanced = ImagePreprocessor.enhance_contrast(img)
    assert enhanced.shape == img.shape

    denoised = ImagePreprocessor.denoise(img, h=5)
    assert denoised.shape == img.shape

    thresh = ImagePreprocessor.threshold(img, method="otsu")
    assert len(thresh.shape) == 2
    assert np.all(np.isin(thresh, [0, 255]))


def test_image_preprocessor_deskew():
    """Validates deskew functionality on synthetic rotated image."""
    # Synthetic white canvas with black text bar
    canvas = np.ones((300, 500), dtype=np.uint8) * 255
    canvas[140:160, 100:400] = 0  # Horizontal bar

    angle = ImagePreprocessor.detect_skew_angle(canvas)
    # The bar is horizontal, skew angle should be very close to 0
    assert abs(angle) < 5.0

    deskewed = ImagePreprocessor.deskew(canvas, angle=0.0)
    assert deskewed.shape[0] >= 300 and deskewed.shape[1] >= 500


def test_image_preprocessor_full_pipeline():
    """Validates process() execution with all options enabled."""
    img = np.ones((200, 300, 3), dtype=np.uint8) * 200
    processed = ImagePreprocessor.process(
        img,
        deskew=True,
        denoise=True,
        enhance=True,
        threshold=False,
        cleanup_border=True,
        max_dim=250,
    )
    assert processed is not None
    assert max(processed.shape[:2]) <= 250


def test_ocr_service_with_provider():
    """Validates OCRService integration with provider and Document Model construction."""
    dummy_provider = DummyOCRProvider()
    service = OCRService(provider=dummy_provider)

    test_img = np.ones((300, 500, 3), dtype=np.uint8) * 255

    elements = service.recognize_image(test_img, preprocess=True)
    assert len(elements) == 2
    assert elements[0].text == "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
    assert elements[1].text == "Độc lập - Tự do - Hạnh phúc"
    assert elements[0].confidence == 0.95

    # Test image to page
    page = service.image_to_page(test_img, page_number=1)
    assert page.page_number == 1
    assert page.width == 500.0
    assert page.height == 300.0
    assert len(page.elements) == 2

    # Test image to document
    doc = service.image_to_document(test_img, title="Test Scanned Image")
    assert doc.metadata.title == "Test Scanned Image"
    assert doc.total_pages == 1
    assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in doc.get_full_text()


def test_invalid_image_loading():
    """Validates exception when loading invalid path or broken bytes."""
    with pytest.raises(InvalidDocumentError):
        ImagePreprocessor.load_image("non_existent_file_12345.png")

    with pytest.raises(InvalidDocumentError):
        ImagePreprocessor.load_image(b"not an image at all")
