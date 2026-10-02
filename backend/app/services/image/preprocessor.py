"""Image preprocessing pipeline for document OCR and cleanup.

Includes deskewing, denoising, contrast enhancement (CLAHE), adaptive binarization,
border cleanup, and flexible resolution resizing.
"""

from pathlib import Path
from typing import Optional, Tuple, Union
import cv2
import numpy as np
from PIL import Image

from app.core.exceptions import InvalidDocumentError
from app.core.logging import logger


class ImagePreprocessor:
    """Configurable preprocessing engine for document images prior to OCR or export."""

    @staticmethod
    def load_image(source: Union[str, Path, bytes, np.ndarray, Image.Image]) -> np.ndarray:
        """Loads an image into a standard OpenCV BGR numpy array."""
        if isinstance(source, np.ndarray):
            return source.copy()

        if isinstance(source, Image.Image):
            # PIL Image to BGR numpy
            rgb = np.array(source.convert("RGB"))
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        if isinstance(source, bytes):
            nparr = np.frombuffer(source, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise InvalidDocumentError("bytes", "Failed to decode image from binary bytes")
            return img

        path = Path(source)
        if not path.exists():
            raise InvalidDocumentError(str(path), "Image file not found")

        # Use imdecode with fromfile to safely handle Windows unicode paths
        try:
            with open(path, "rb") as f:
                img_bytes = f.read()
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise InvalidDocumentError(str(path), "Unable to decode image file format")
            return img
        except Exception as e:
            raise InvalidDocumentError(str(path), f"Failed to read image: {e}")

    @staticmethod
    def to_grayscale(image: np.ndarray) -> np.ndarray:
        """Converts an image to single-channel grayscale if needed."""
        if len(image.shape) == 2:
            return image
        if len(image.shape) == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def resize(
        image: np.ndarray,
        max_dim: Optional[int] = None,
        scale: Optional[float] = None,
    ) -> np.ndarray:
        """Resizes image maintaining aspect ratio."""
        h, w = image.shape[:2]

        if scale is not None and scale > 0 and scale != 1.0:
            new_w, new_h = int(w * scale), int(h * scale)
            return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)

        if max_dim is not None and max(h, w) > max_dim:
            factor = max_dim / float(max(h, w))
            new_w, new_h = int(w * factor), int(h * factor)
            return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

        return image

    @staticmethod
    def denoise(image: np.ndarray, h: int = 10) -> np.ndarray:
        """Applies Non-Local Means denoising or bilateral filtering."""
        if len(image.shape) == 2:
            return cv2.fastNlMeansDenoising(image, None, h, 7, 21)
        return cv2.fastNlMeansDenoisingColored(image, None, h, h, 7, 21)

    @staticmethod
    def enhance_contrast(
        image: np.ndarray,
        clip_limit: float = 2.0,
        tile_grid_size: Tuple[int, int] = (8, 8),
    ) -> np.ndarray:
        """Enhances contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)

        if len(image.shape) == 2:
            return clahe.apply(image)

        # For color images, apply CLAHE to L channel in LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        cl = clahe.apply(l)
        merged = cv2.merge((cl, a, b))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    @staticmethod
    def threshold(image: np.ndarray, method: str = "otsu") -> np.ndarray:
        """Converts image to binary black & white using Otsu or adaptive Gaussian thresholding."""
        gray = ImagePreprocessor.to_grayscale(image)

        if method == "adaptive":
            return cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
            )

        # Otsu thresholding
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    @staticmethod
    def detect_skew_angle(image: np.ndarray) -> float:
        """Detects document skew angle in degrees using minimum bounding box of text lines."""
        gray = ImagePreprocessor.to_grayscale(image)
        # Invert colors: text = white, background = black
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Use morphological dilation to connect text glyphs into line blocks
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        dilated = cv2.dilate(thresh, kernel, iterations=2)

        # Find text contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        angles = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 500:  # Ignore tiny noise
                continue
            rect = cv2.minAreaRect(cnt)
            angle = rect[-1]
            if angle < -45:
                angle = -(90 + angle)
            elif angle > 45:
                angle = 90 - angle
            else:
                angle = -angle

            if abs(angle) < 45.0:  # Only consider reasonable document tilt
                angles.append(angle)

        if not angles:
            return 0.0

        # Return median angle to be robust against outliers
        return float(np.median(angles))

    @staticmethod
    def deskew(image: np.ndarray, angle: Optional[float] = None) -> np.ndarray:
        """Rotates image to correct document tilt."""
        if angle is None:
            angle = ImagePreprocessor.detect_skew_angle(image)

        if abs(angle) < 0.2:  # Negligible skew
            return image

        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Adjust bounding box size to avoid clipping rotated corners
        cos = np.abs(rotation_matrix[0, 0])
        sin = np.abs(rotation_matrix[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        rotation_matrix[0, 2] += (new_w / 2) - center[0]
        rotation_matrix[1, 2] += (new_h / 2) - center[1]

        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated

    @staticmethod
    def cleanup_border(image: np.ndarray, border_fraction: float = 0.02) -> np.ndarray:
        """Removes dark scanning borders around the image perimeter."""
        h, w = image.shape[:2]
        pad_y = int(h * border_fraction)
        pad_x = int(w * border_fraction)

        if pad_y <= 0 or pad_x <= 0:
            return image

        # Inset image slightly
        return image[pad_y : h - pad_y, pad_x : w - pad_x].copy()

    @classmethod
    def process(
        cls,
        source: Union[str, Path, bytes, np.ndarray, Image.Image],
        deskew: bool = True,
        denoise: bool = True,
        enhance: bool = True,
        threshold: bool = False,
        cleanup_border: bool = False,
        max_dim: Optional[int] = None,
    ) -> np.ndarray:
        """Executes a configurable preprocessing pipeline on the input image.

        Args:
            source: Image input (path, bytes, ndarray, or PIL Image).
            deskew: Whether to correct tilt angle.
            denoise: Whether to remove scan noise.
            enhance: Whether to apply CLAHE contrast enhancement.
            threshold: Whether to binarize to pure black & white.
            cleanup_border: Whether to trim scanner edge artifacts.
            max_dim: Max dimension to resize.

        Returns:
            Preprocessed image as OpenCV numpy ndarray.
        """
        img = cls.load_image(source)

        if max_dim:
            img = cls.resize(img, max_dim=max_dim)

        if cleanup_border:
            img = cls.cleanup_border(img)

        if deskew:
            try:
                img = cls.deskew(img)
            except Exception as e:
                logger.warning(f"Deskewing step failed, keeping original orientation: {e}")

        if denoise:
            try:
                img = cls.denoise(img)
            except Exception as e:
                logger.warning(f"Denoising step skipped: {e}")

        if enhance:
            try:
                img = cls.enhance_contrast(img)
            except Exception as e:
                logger.warning(f"Contrast enhancement step skipped: {e}")

        if threshold:
            try:
                img = cls.threshold(img)
            except Exception as e:
                logger.warning(f"Thresholding step skipped: {e}")

        return img

    @staticmethod
    def to_pil(image: np.ndarray) -> Image.Image:
        """Converts an OpenCV image array to a PIL Image."""
        if len(image.shape) == 2:
            return Image.fromarray(image)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)
