"""File type detection module using magic bytes (signatures) and extensions.

Supports robust offline file type identification for PDF, DOCX, raster images,
and Office Open XML formats without external C-library dependencies.
"""

from enum import Enum
from pathlib import Path
from typing import Optional, Union
import zipfile
import io


class FileType(str, Enum):
    """Supported file formats."""
    PDF = "pdf"
    DOCX = "docx"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    XLSX = "xlsx"
    PPTX = "pptx"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "md"
    UNKNOWN = "unknown"

    @property
    def is_image(self) -> bool:
        return self in (FileType.JPEG, FileType.PNG, FileType.WEBP)

    @property
    def is_document(self) -> bool:
        return self in (FileType.PDF, FileType.DOCX, FileType.TXT, FileType.HTML, FileType.MARKDOWN)


# Common file signatures (magic bytes)
SIGNATURES = {
    b"%PDF-": FileType.PDF,
    b"\x89PNG\r\n\x1a\n": FileType.PNG,
    b"\xff\xd8\xff": FileType.JPEG,
}

EXTENSION_MAP = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
    ".jpg": FileType.JPEG,
    ".jpeg": FileType.JPEG,
    ".png": FileType.PNG,
    ".webp": FileType.WEBP,
    ".xlsx": FileType.XLSX,
    ".pptx": FileType.PPTX,
    ".txt": FileType.TXT,
    ".html": FileType.HTML,
    ".htm": FileType.HTML,
    ".md": FileType.MARKDOWN,
    ".markdown": FileType.MARKDOWN,
}


def _detect_zip_format(data_or_path: Union[Path, bytes]) -> FileType:
    """Disambiguates ZIP-based OpenXML documents (DOCX, XLSX, PPTX)."""
    try:
        zf = (
            zipfile.ZipFile(data_or_path, "r")
            if isinstance(data_or_path, (str, Path))
            else zipfile.ZipFile(io.BytesIO(data_or_path), "r")
        )
        with zf:
            namelist = set(zf.namelist())
            if any(name.startswith("word/") for name in namelist):
                return FileType.DOCX
            if any(name.startswith("xl/") for name in namelist):
                return FileType.XLSX
            if any(name.startswith("ppt/") for name in namelist):
                return FileType.PPTX
    except Exception:
        pass
    return FileType.UNKNOWN


def detect_file_type(target: Union[str, Path, bytes]) -> FileType:
    """Detects file format using byte signatures first, then extension if needed.

    Args:
        target: File path (str or Path) or binary bytes.

    Returns:
        FileType enum member.
    """
    path: Optional[Path] = None
    header: bytes = b""

    if isinstance(target, (str, Path)):
        path = Path(target)
        if path.exists() and path.is_file():
            try:
                with open(path, "rb") as f:
                    header = f.read(64)
            except Exception:
                header = b""
    elif isinstance(target, bytes):
        header = target[:64]

    # 1. Check Magic Bytes
    if header.startswith(b"%PDF-"):
        return FileType.PDF

    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return FileType.PNG

    if header.startswith(b"\xff\xd8\xff"):
        return FileType.JPEG

    if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return FileType.WEBP

    # 2. Check ZIP-based container (DOCX / XLSX / PPTX)
    if header.startswith(b"PK\x03\x04"):
        detected_zip = _detect_zip_format(path if path else (target if isinstance(target, bytes) else b""))
        if detected_zip != FileType.UNKNOWN:
            return detected_zip
        if path and path.suffix.lower() in EXTENSION_MAP:
            return EXTENSION_MAP[path.suffix.lower()]

    # 3. Fallback to extension check
    if path and path.suffix:
        ext = path.suffix.lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

    return FileType.UNKNOWN
