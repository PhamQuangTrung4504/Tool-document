"""Conversion service coordinating format transformations through the intermediate Document model."""

from pathlib import Path
from typing import Optional, Union

from app.core.exceptions import ConversionError, DocumentError, InvalidDocumentError
from app.core.logging import logger
from app.exporters import get_exporter
from app.models.document import Document
from app.models.enums import OCRMode
from app.core.cancellation import CancellationToken, OperationCancelledError
from app.services.document.loader import DocumentLoader
from app.services.ocr.ocr_service import OCRService, get_ocr_service
from app.utils.file_type import detect_file_type


class ConversionService:
    """Central orchestration service for converting between heterogeneous document formats."""

    def __init__(
        self,
        loader: Optional[DocumentLoader] = None,
        ocr_service: Optional[OCRService] = None,
    ) -> None:
        self.ocr_service = ocr_service or get_ocr_service()
        self.loader = loader or DocumentLoader(ocr_service=self.ocr_service)

    def convert(
        self,
        input_path: Union[str, Path],
        to_format: str,
        output_path: Optional[Union[str, Path]] = None,
        force_ocr: bool = False,
        lang: Optional[str] = None,
        mode: Union[OCRMode, str] = OCRMode.FAST,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> Path:
        """Converts an input document or image to the requested target format.

        Architecture strictly adheres to:
        Input -> Loader/OCR -> Document Model -> Exporter -> Output.

        Args:
            input_path: Source file path.
            to_format: Target format extension (e.g. 'docx', 'pdf', 'txt', 'html', 'md').
            output_path: Optional destination file path. Defaults to same stem with new extension.
            force_ocr: Whether to force OCR recognition.
            lang: Language code for OCR processing.
            mode: OCRMode (FAST, FULL, or AUTO). Defaults to FAST.
            cancellation_token: Optional cancellation token.

        Returns:
            Resolved Path of the converted file.
        """
        source_file = Path(input_path)
        if not source_file.exists():
            raise InvalidDocumentError(str(source_file), "Source file does not exist")

        target_ext = to_format.lower().lstrip(".")
        if output_path is None:
            destination = source_file.with_suffix(f".{target_ext}")
        else:
            destination = Path(output_path)

        source_type = detect_file_type(source_file).value

        logger.info(f"Starting conversion: {source_file.name} [{source_type}] -> {destination.name} [{target_ext}] (mode={mode})")

        try:
            if cancellation_token and cancellation_token.is_cancelled:
                raise OperationCancelledError()

            # 1. Load source file into intermediate Document model
            document: Document = self.loader.load(
                source=source_file,
                force_ocr=force_ocr,
                lang=lang,
                mode=mode,
                cancellation_token=cancellation_token,
            )

            if cancellation_token and cancellation_token.is_cancelled:
                raise OperationCancelledError()

            # 2. Retrieve appropriate exporter
            exporter = get_exporter(target_ext)

            # 3. Export Document model to target format
            resolved_output = exporter.export(document, destination)

            logger.info(f"Successfully converted to {resolved_output}")
            return resolved_output

        except DocumentError:
            # Re-raise known document errors without wrapping
            raise
        except Exception as e:
            raise ConversionError(
                source_format=source_type,
                target_format=target_ext,
                reason=str(e),
            )
