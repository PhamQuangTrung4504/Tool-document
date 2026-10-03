"""Standard Local IPC (Inter-Process Communication) JSON contract handler.

Provides a robust, decoupled JSON-RPC / IPC interface for Tauri desktop frontends,
with strict schema validation, objective metrics, and secure error masking.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.core.exceptions import (
    ConversionError,
    DocumentAssistantError,
    InvalidDocumentError,
    OCRProcessingError,
    UnsupportedFormatError,
)
from app.core.logging import logger
from app.models.enums import OCRMode
from app.services.batch.job import OperationCancelledError
from app.services.converter.converter_service import ConversionService
from app.services.fidelity.fidelity_service import DocumentFidelityService
from app.services.ocr.ocr_service import OCRService
from app.services.pdf.analyzer import analyze_pdf
from app.services.pdf.pdf_service import PDFService


class IPCHandler:
    """Dispatches JSON IPC requests to internal engine services."""

    def __init__(
        self,
        conversion_service: Optional[ConversionService] = None,
        ocr_service: Optional[OCRService] = None,
        pdf_service: Optional[PDFService] = None,
    ) -> None:
        self.ocr_service = ocr_service or OCRService()
        self.conversion_service = conversion_service or ConversionService(ocr_service=self.ocr_service)
        self.pdf_service = pdf_service or PDFService(ocr_service=self.ocr_service)

    def handle(self, request_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Processes an IPC request and returns a standard JSON-compatible dictionary."""
        t0 = time.perf_counter()

        # 1. Parse JSON if string
        if isinstance(request_data, str):
            try:
                request = json.loads(request_data.lstrip("\ufeff"))
            except Exception as e:
                return {
                    "success": False,
                    "error": {
                        "code": "INVALID_JSON",
                        "message": f"Malformed JSON request: {e}",
                    },
                }
        elif isinstance(request_data, dict):
            request = request_data
        else:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_REQUEST_TYPE",
                    "message": "Request must be a JSON string or dictionary.",
                },
            }

        operation = request.get("operation")
        if not operation or not isinstance(operation, str):
            return {
                "success": False,
                "error": {
                    "code": "MISSING_OPERATION",
                    "message": "Request missing required 'operation' field.",
                },
            }

        op = operation.lower().strip()
        input_target = request.get("input")
        output_target = request.get("output")
        options = request.get("options", {})

        try:
            if op == "convert":
                response = self._handle_convert(input_target, output_target, options, t0)
            elif op == "ocr":
                response = self._handle_ocr(input_target, output_target, options, t0)
            elif op == "info":
                response = self._handle_info(input_target, options, t0)
            elif op == "merge":
                response = self._handle_merge(input_target, output_target, options, t0)
            elif op == "split":
                response = self._handle_split(input_target, output_target, options, t0)
            elif op == "list_files":
                response = self._handle_list_files(input_target, options, t0)
            else:
                return {
                    "success": False,
                    "error": {
                        "code": "UNSUPPORTED_OPERATION",
                        "message": f"Operation '{op}' is not supported.",
                    },
                }

            return response

        except InvalidDocumentError as e:
            logger.warning(f"IPC InvalidDocumentError: {e}")
            return {"success": False, "error": {"code": "INVALID_DOCUMENT_ERROR", "message": str(e)}}
        except UnsupportedFormatError as e:
            logger.warning(f"IPC UnsupportedFormatError: {e}")
            return {"success": False, "error": {"code": "UNSUPPORTED_FORMAT_ERROR", "message": str(e)}}
        except OCRProcessingError as e:
            logger.error(f"IPC OCRProcessingError: {e}")
            return {"success": False, "error": {"code": "OCR_PROCESSING_ERROR", "message": str(e)}}
        except OperationCancelledError:
            logger.info("IPC operation cancelled by user")
            return {"success": False, "error": {"code": "OPERATION_CANCELLED", "message": "Thao tác đã bị hủy bởi người dùng."}}
        except ConversionError as e:
            logger.error(f"IPC ConversionError: {e}")
            return {"success": False, "error": {"code": "CONVERSION_ERROR", "message": str(e)}}
        except FileNotFoundError as e:
            return {"success": False, "error": {"code": "FILE_NOT_FOUND", "message": f"Không tìm thấy file: {e}"}}
        except Exception as e:
            logger.exception(f"Unexpected IPC internal error: {e}")
            # Strict security: mask raw stack trace
            return {
                "success": False,
                "error": {
                    "code": "INTERNAL_PROCESSING_ERROR",
                    "message": "Đã xảy ra lỗi nội bộ trong quá trình xử lý tài liệu.",
                },
            }

    def _handle_convert(
        self,
        input_path: Any,
        output_path: Any,
        options: Dict[str, Any],
        start_time: float,
    ) -> Dict[str, Any]:
        if not input_path:
            raise InvalidDocumentError("", "Missing 'input' path in convert request")

        in_p = Path(input_path)
        out_p = Path(output_path) if output_path else None
        to_format = options.get("to_format", "docx")
        ocr_mode_str = options.get("ocr_mode", "fast")
        lang = options.get("lang")
        force_ocr = bool(options.get("force_ocr", False))

        ocr_mode = OCRMode(ocr_mode_str) if ocr_mode_str in OCRMode._value2member_map_ else OCRMode.FAST

        # Run conversion
        converted_path = self.conversion_service.convert(
            input_path=in_p,
            to_format=to_format,
            output_path=out_p,
            force_ocr=force_ocr,
            lang=lang,
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Inspect resulting pages if possible
        page_count = 1
        if in_p.suffix.lower() == ".pdf":
            try:
                import pymupdf
                with pymupdf.open(str(in_p)) as doc:
                    page_count = len(doc)
            except Exception:
                pass

        return {
            "success": True,
            "operation": "convert",
            "output": str(converted_path),
            "metrics": {
                "pages": page_count,
                "processing_time_ms": elapsed_ms,
                "ocr_mode": ocr_mode.value,
            },
            "warnings": [],
        }

    def _handle_ocr(
        self,
        input_path: Any,
        output_path: Any,
        options: Dict[str, Any],
        start_time: float,
    ) -> Dict[str, Any]:
        if not input_path:
            raise InvalidDocumentError("", "Missing 'input' path in ocr request")

        in_p = Path(input_path)
        lang = options.get("lang", "vi")
        ocr_mode_str = options.get("ocr_mode", "fast")
        ocr_mode = OCRMode(ocr_mode_str) if ocr_mode_str in OCRMode._value2member_map_ else OCRMode.FAST

        if in_p.suffix.lower() == ".pdf":
            out_p = Path(output_path) if output_path else in_p.with_name(f"{in_p.stem}_searchable.pdf")
            self.pdf_service.create_searchable_pdf(in_p, out_p, lang=lang)
            final_out = str(out_p)
        else:
            # Image OCR
            elements = self.ocr_service.recognize_image(in_p, mode=ocr_mode, lang=lang)
            final_out = [e.model_dump() for e in elements]

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "success": True,
            "operation": "ocr",
            "output": final_out,
            "metrics": {
                "processing_time_ms": elapsed_ms,
                "ocr_mode": ocr_mode.value,
            },
            "warnings": [],
        }

    def _handle_info(self, input_path: Any, options: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        if not input_path:
            raise InvalidDocumentError("", "Missing 'input' path in info request")

        in_p = Path(input_path)
        if not in_p.exists():
            raise FileNotFoundError(str(in_p))

        size_bytes = in_p.stat().st_size if in_p.is_file() else 0
        ext = in_p.suffix.lower()

        if ext == ".pdf":
            structure = analyze_pdf(in_p)
            info_data = structure.model_dump()
            info_data["page_count"] = structure.total_pages
            info_data["total_pages"] = structure.total_pages
            info_data["size_bytes"] = size_bytes
            info_data["title"] = structure.title or in_p.stem
            info_data["filename"] = in_p.name
            info_data["suffix"] = ext
            info_data["pdf_type"] = structure.pdf_type.value
        elif ext == ".docx":
            try:
                from docx import Document as DocxDoc
                docx_d = DocxDoc(str(in_p))
                para_count = len(docx_d.paragraphs)
                table_count = len(docx_d.tables)
                page_est = max(1, (para_count + 3) // 4)
            except Exception:
                para_count = 0
                table_count = 0
                page_est = 1

            info_data = {
                "filename": in_p.name,
                "title": in_p.stem,
                "size_bytes": size_bytes,
                "suffix": ext,
                "paragraph_count": para_count,
                "table_count": table_count,
                "page_count": page_est,
                "total_pages": page_est,
            }
        elif ext in (".txt", ".md"):
            try:
                content = in_p.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                page_est = max(1, (len(lines) + 44) // 45)
            except Exception:
                lines = []
                page_est = 1

            info_data = {
                "filename": in_p.name,
                "title": in_p.stem,
                "size_bytes": size_bytes,
                "suffix": ext,
                "line_count": len(lines),
                "page_count": page_est,
                "total_pages": page_est,
            }
        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"):
            try:
                from PIL import Image
                with Image.open(in_p) as img:
                    w, h = img.size
            except Exception:
                w, h = 0, 0

            info_data = {
                "filename": in_p.name,
                "title": in_p.stem,
                "size_bytes": size_bytes,
                "suffix": ext,
                "width": w,
                "height": h,
                "page_count": 1,
                "total_pages": 1,
            }
        else:
            info_data = {
                "filename": in_p.name,
                "title": in_p.stem,
                "size_bytes": size_bytes,
                "suffix": ext,
                "page_count": 1,
                "total_pages": 1,
            }

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return {
            "success": True,
            "operation": "info",
            "output": info_data,
            "metrics": {"processing_time_ms": elapsed_ms},
            "warnings": [],
        }

    def _handle_merge(
        self,
        inputs: Any,
        output_path: Any,
        options: Dict[str, Any],
        start_time: float,
    ) -> Dict[str, Any]:
        if not isinstance(inputs, list) or len(inputs) < 2:
            raise InvalidDocumentError("", "Merge operation requires at least 2 input files in a list")
        if not output_path:
            raise InvalidDocumentError("", "Merge operation requires an output path")

        out_p = Path(output_path)
        self.pdf_service.merge_pdfs(inputs, out_p)
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return {
            "success": True,
            "operation": "merge",
            "output": str(out_p),
            "metrics": {"processing_time_ms": elapsed_ms, "input_count": len(inputs)},
            "warnings": [],
        }

    def _handle_split(
        self,
        input_path: Any,
        output_path: Any,
        options: Dict[str, Any],
        start_time: float,
    ) -> Dict[str, Any]:
        if not input_path:
            raise InvalidDocumentError("", "Missing 'input' path in split request")

        in_p = Path(input_path)
        if output_path:
            out_dir = Path(output_path)
        else:
            out_dir = in_p.parent / f"{in_p.stem}_split"
        out_dir.mkdir(parents=True, exist_ok=True)

        pages_per_split = int(options.get("pages_per_split", 1)) if options.get("pages_per_split") else 1
        page_ranges = options.get("page_ranges")

        created_files = self.pdf_service.split_pdf(
            in_p,
            out_dir,
            page_ranges=page_ranges,
            pages_per_split=pages_per_split,
        )
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return {
            "success": True,
            "operation": "split",
            "output": [str(p) for p in created_files],
            "metrics": {"processing_time_ms": elapsed_ms, "chunks": len(created_files)},
            "warnings": [],
        }

    def _handle_list_files(
        self,
        folder_path: Any,
        options: Dict[str, Any],
        start_time: float,
    ) -> Dict[str, Any]:
        if not folder_path:
            raise InvalidDocumentError("", "Missing folder path in list_files request")

        f_path = Path(folder_path)
        if not f_path.exists() or not f_path.is_dir():
            raise InvalidDocumentError(str(f_path), "Directory does not exist or is not a directory")

        supported = {"pdf", "docx", "png", "jpg", "jpeg", "bmp", "tiff", "txt", "md", "html", "htm"}
        items = []

        try:
            for entry in f_path.iterdir():
                if entry.is_file():
                    ext = entry.suffix.lstrip(".").lower()
                    if ext in supported:
                        items.append({
                            "name": entry.name,
                            "path": str(entry),
                            "size_bytes": entry.stat().st_size,
                            "ext": ext,
                        })
        except Exception as e:
            logger.warning(f"Error reading directory {f_path}: {e}")

        items.sort(key=lambda x: x["name"].lower())
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return {
            "success": True,
            "operation": "list_files",
            "output": items,
            "metrics": {"processing_time_ms": elapsed_ms, "count": len(items)},
            "warnings": [],
        }
