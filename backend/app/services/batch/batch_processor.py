"""Batch processing engine for bulk document operations.

Processes single or multiple files with progress callbacks, success/failure tracking,
and resilient error isolation so single-file failures do not halt batch jobs.
"""

from pathlib import Path
import time
from typing import Callable, List, Optional, Union
from pydantic import BaseModel, Field

from app.core.exceptions import DocumentError
from app.core.logging import logger
from app.services.converter.converter_service import ConversionService
from app.services.ocr.ocr_service import OCRService, get_ocr_service
from app.services.pdf.pdf_service import PDFService


class BatchItemResult(BaseModel):
    """Result summary for an individual document in a batch."""
    file_path: Path
    status: str = Field(..., description="'success' or 'failed'")
    output_path: Optional[Path] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0


class BatchReport(BaseModel):
    """Cumulative report summarizing batch execution."""
    total: int
    succeeded: int = 0
    failed: int = 0
    results: List[BatchItemResult] = Field(default_factory=list)
    total_duration_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        return (self.succeeded / self.total * 100.0) if self.total > 0 else 0.0


class BatchProcessor:
    """Manages batch operations across collections of documents."""

    def __init__(
        self,
        converter: Optional[ConversionService] = None,
        ocr_service: Optional[OCRService] = None,
        pdf_service: Optional[PDFService] = None,
    ) -> None:
        self.converter = converter or ConversionService()
        self.ocr_service = ocr_service or get_ocr_service()
        self.pdf_service = pdf_service or PDFService(ocr_service=self.ocr_service)

    def process(
        self,
        files: List[Union[str, Path]],
        operation: Callable[[Path], Optional[Path]],
        progress_callback: Optional[Callable[[int, int, Path], None]] = None,
    ) -> BatchReport:
        """Executes a custom operation sequentially over a list of document files.

        Args:
            files: List of file paths to process.
            operation: Function accepting a source file Path and returning output Path.
            progress_callback: Optional callback `(current_index, total_count, current_path)`.

        Returns:
            BatchReport containing success/failure statistics and per-item results.
        """
        total = len(files)
        report = BatchReport(total=total)
        batch_start_time = time.perf_counter()

        for idx, file_item in enumerate(files):
            file_path = Path(file_item)
            item_start = time.perf_counter()

            if progress_callback:
                try:
                    progress_callback(idx + 1, total, file_path)
                except Exception as cb_err:
                    logger.debug(f"Progress callback raised an exception: {cb_err}")

            if not file_path.exists():
                report.failed += 1
                report.results.append(
                    BatchItemResult(
                        file_path=file_path,
                        status="failed",
                        error_message="File does not exist",
                        duration_seconds=time.perf_counter() - item_start,
                    )
                )
                continue

            try:
                out_path = operation(file_path)
                duration = time.perf_counter() - item_start
                report.succeeded += 1
                report.results.append(
                    BatchItemResult(
                        file_path=file_path,
                        status="success",
                        output_path=out_path,
                        duration_seconds=duration,
                    )
                )
            except DocumentError as de:
                duration = time.perf_counter() - item_start
                report.failed += 1
                report.results.append(
                    BatchItemResult(
                        file_path=file_path,
                        status="failed",
                        error_message=str(de),
                        duration_seconds=duration,
                    )
                )
            except Exception as ex:
                duration = time.perf_counter() - item_start
                report.failed += 1
                report.results.append(
                    BatchItemResult(
                        file_path=file_path,
                        status="failed",
                        error_message=f"Unexpected error: {ex}",
                        duration_seconds=duration,
                    )
                )

        report.total_duration_seconds = time.perf_counter() - batch_start_time
        return report

    def convert_all(
        self,
        files: List[Union[str, Path]],
        to_format: str,
        output_dir: Optional[Union[str, Path]] = None,
        progress_callback: Optional[Callable[[int, int, Path], None]] = None,
    ) -> BatchReport:
        """Converts multiple documents to the target format."""
        out_directory = Path(output_dir) if output_dir else None
        if out_directory:
            out_directory.mkdir(parents=True, exist_ok=True)

        def _convert_op(path: Path) -> Path:
            dest = (out_directory / f"{path.stem}.{to_format}") if out_directory else None
            return self.converter.convert(path, to_format=to_format, output_path=dest)

        return self.process(files, _convert_op, progress_callback=progress_callback)
