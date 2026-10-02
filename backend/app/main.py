"""CLI Entry Point for Document Assistant Backend.

Provides a robust command-line interface on Windows PowerShell for document inspection,
OCR extraction, multi-format conversion, PDF merging, and PDF splitting.
"""

import argparse
from pathlib import Path
import sys
from typing import List, Optional

from app.core.exceptions import DocumentError
from app.core.logging import logger, setup_logger
from app.services.converter.converter_service import ConversionService
from app.services.document.loader import DocumentLoader
from app.services.image.preprocessor import ImagePreprocessor
from app.services.ocr.ocr_service import get_ocr_service
from app.services.pdf.analyzer import analyze_pdf
from app.services.pdf.pdf_service import PDFService
from app.utils.file_type import FileType, detect_file_type


def cmd_info(args: argparse.Namespace) -> int:
    """Displays structural metadata and content analysis of a document."""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File '{file_path}' does not exist.", file=sys.stderr)
        return 1

    ftype = detect_file_type(file_path)
    size_kb = file_path.stat().st_size / 1024.0

    print("=" * 50)
    print(f"Document Assistant - File Inspection")
    print("=" * 50)
    print(f"File Name   : {file_path.name}")
    print(f"Path        : {file_path.resolve()}")
    print(f"Detected Type: {ftype.value.upper()}")
    print(f"Size        : {size_kb:.2f} KB")

    if ftype == FileType.PDF:
        analysis = analyze_pdf(file_path)
        print(f"Total Pages : {analysis.total_pages}")
        print(f"PDF Type    : {analysis.pdf_type.value.upper()} (Scanned / Text / Mixed)")
        if analysis.title:
            print(f"Title       : {analysis.title}")
        if analysis.author:
            print(f"Author      : {analysis.author}")
        print("\nPage Breakdown:")
        for p in analysis.pages:
            scanned_str = "[SCANNED]" if p.is_scanned else "[TEXT LAYER]"
            print(f"  Page {p.page_number:2d}: {p.char_count:4d} chars, {p.image_count} images - {scanned_str}")

    elif ftype.is_image:
        img = ImagePreprocessor.load_image(file_path)
        h, w = img.shape[:2]
        channels = img.shape[2] if len(img.shape) > 2 else 1
        print(f"Dimensions  : {w} x {h} px")
        print(f"Channels    : {channels}")

    elif ftype == FileType.DOCX:
        loader = DocumentLoader()
        doc = loader.load(file_path)
        print(f"Paragraphs  : {len(doc.pages[0].get_text_elements())}")
        print(f"Tables      : {len(doc.pages[0].get_tables())}")

    print("=" * 50)
    return 0


def cmd_ocr(args: argparse.Namespace) -> int:
    """Executes OCR on an image or document and prints or saves extracted text."""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        return 1

    print(f"Executing OCR on: {input_path.name} (Language: {args.lang})...")
    ocr_service = get_ocr_service()

    ftype = detect_file_type(input_path)
    if ftype.is_image:
        elements = ocr_service.recognize_image(
            source=input_path,
            preprocess=not args.no_preprocess,
            lang=args.lang,
        )
        extracted_text = "\n".join(el.text for el in elements if el.text.strip())
    elif ftype == FileType.PDF:
        pdf_service = PDFService(ocr_service=ocr_service)
        doc = pdf_service.parse_to_document(input_path, force_ocr=True)
        extracted_text = doc.get_full_text()
    else:
        print(f"Error: OCR is only supported on images and PDFs.", file=sys.stderr)
        return 1

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(extracted_text, encoding="utf-8")
        print(f"OCR text written to: {out_p.resolve()}")
    else:
        print("\n--- OCR Extracted Text ---")
        print(extracted_text)
        print("--------------------------")

    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    """Converts a document between supported formats."""
    conv_service = ConversionService()
    try:
        output_file = conv_service.convert(
            input_path=args.input,
            to_format=args.to,
            output_path=args.output,
            force_ocr=args.force_ocr,
            lang=args.lang,
            mode=getattr(args, "ocr_mode", "fast"),
        )
        print(f"Success: Converted '{args.input}' to '{output_file}'")
        return 0
    except DocumentError as de:
        print(f"Conversion Error: {de}", file=sys.stderr)
        return 1


def cmd_merge(args: argparse.Namespace) -> int:
    """Merges multiple PDF files into one output PDF."""
    pdf_service = PDFService()
    try:
        out = pdf_service.merge_pdfs(args.files, args.output)
        print(f"Success: Merged {len(args.files)} files into '{out}'")
        return 0
    except DocumentError as de:
        print(f"Merge Error: {de}", file=sys.stderr)
        return 1


def cmd_split(args: argparse.Namespace) -> int:
    """Splits a PDF by page ranges or individual pages."""
    pdf_service = PDFService()
    try:
        out_dir = args.output_dir or Path(args.input).parent / f"{Path(args.input).stem}_split"
        created = pdf_service.split_pdf(args.input, out_dir, page_ranges=args.pages)
        print(f"Success: Created {len(created)} split file(s) in '{out_dir}'")
        for f in created:
            print(f"  - {f.name}")
        return 0
    except DocumentError as de:
        print(f"Split Error: {de}", file=sys.stderr)
        return 1


def cmd_ipc(args: argparse.Namespace) -> int:
    """Executes IPC request using JSON payload and outputs JSON response."""
    import json
    from app.core.ipc import IPCHandler

    handler = IPCHandler()
    if args.stdin:
        raw_payload = sys.stdin.read().lstrip("\ufeff")
    else:
        raw_payload = args.payload.lstrip("\ufeff")

    response = handler.handle(raw_payload)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if response.get("success") else 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI argument parser and dispatcher."""
    parser = argparse.ArgumentParser(
        prog="document-assistant",
        description="Document Assistant Backend - Offline Windows Document & OCR Engine",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging output")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: info
    p_info = subparsers.add_parser("info", help="Inspect document structure, type, and metadata")
    p_info.add_argument("file", help="Path to document or image file")

    # Command: ocr
    p_ocr = subparsers.add_parser("ocr", help="Run OCR text extraction on image or scanned PDF")
    p_ocr.add_argument("input", help="Image or PDF file path")
    p_ocr.add_argument("--output", "-o", help="Optional text file path to write results to")
    p_ocr.add_argument("--lang", default="vi", help="OCR language code (default: 'vi')")
    p_ocr.add_argument("--ocr-mode", choices=["fast", "full", "auto"], default="fast", help="OCR mode (default: fast)")
    p_ocr.add_argument("--no-preprocess", action="store_true", help="Disable image deskew and contrast preprocessing")

    # Command: convert
    p_conv = subparsers.add_parser("convert", help="Convert document between formats")
    p_conv.add_argument("input", help="Source file path")
    p_conv.add_argument("--to", required=True, help="Target format (docx, pdf, txt, html, md)")
    p_conv.add_argument("--output", "-o", help="Optional output destination path")
    p_conv.add_argument("--force-ocr", action="store_true", help="Force OCR extraction on PDF")
    p_conv.add_argument("--lang", default="vi", help="Language code if OCR is required")
    p_conv.add_argument("--ocr-mode", choices=["fast", "full", "auto"], default="fast", help="OCR mode (default: fast)")

    # Command: merge
    p_merge = subparsers.add_parser("merge", help="Merge multiple PDF files into one")
    p_merge.add_argument("files", nargs="+", help="PDF files to merge in sequential order")
    p_merge.add_argument("--output", "-o", required=True, help="Merged output PDF path")

    # Command: split
    p_split = subparsers.add_parser("split", help="Split a PDF by page ranges")
    p_split.add_argument("input", help="Source PDF file path")
    p_split.add_argument("--pages", help="Page ranges (e.g. '1-3, 5') or omit for all pages")
    p_split.add_argument("--output-dir", "-o", help="Directory where split files are saved")

    # Command: ipc
    p_ipc = subparsers.add_parser("ipc", help="Execute JSON IPC request for desktop frontend")
    p_ipc.add_argument("payload", nargs="?", default="", help="JSON request payload string")
    p_ipc.add_argument("--stdin", action="store_true", help="Read JSON request payload from standard input")

    args = parser.parse_args(argv)

    if args.debug:
        setup_logger(level="DEBUG")

    if not args.command:
        parser.print_help()
        return 0

    command_handlers = {
        "info": cmd_info,
        "ocr": cmd_ocr,
        "convert": cmd_convert,
        "merge": cmd_merge,
        "split": cmd_split,
        "ipc": cmd_ipc,
    }

    handler = command_handlers.get(args.command)
    if handler:
        try:
            return handler(args)
        except Exception as e:
            if args.debug:
                raise
            print(f"Execution Error: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
