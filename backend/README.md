# Document Assistant Backend Engine

> **Offline-first Document Processing Engine for Windows**
> 
> Được xây dựng bởi Senior Software Architect & Senior Python Developer. Cung cấp kiến trúc module chuẩn mực để xử lý tài liệu, OCR tiếng Việt, trích xuất cấu trúc layout, và chuyển đổi giữa nhiều định dạng hoàn toàn OFFLINE trên Windows.

---

## 1. Kiến trúc Tổng quan (Architecture)

Toàn bộ hệ thống tuân thủ nguyên tắc **Decoupled Architecture** với **Intermediate Document Model**. Tuyệt đối không cho phép các định dạng convert trực tiếp sang nhau (như PDF → DOCX hay JPG → DOCX).

```text
                           ┌─────────────────────────┐
                           │   Input File / Stream   │
                           │(PDF, DOCX, JPG, PNG...) │
                           └────────────┬────────────┘
                                        │
                         [Detect MIME / Magic Bytes]
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │          Parsers / OCR Services           │
                  │  ┌──────────────┐       ┌──────────────┐  │
                  │  │  PyMuPDF     │       │  PaddleOCR   │  │
                  │  │ (Text/Images)│       │  Tesseract   │  │
                  │  └──────────────┘       └──────────────┘  │
                  │  ┌──────────────┐       ┌──────────────┐  │
                  │  │ python-docx  │       │ Preprocessor │  │
                  │  │(Styles/Table)│       │(Deskew/CLAHE)│  │
                  │  └──────────────┘       └──────────────┘  │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                 ┌─────────────────────────────────────────────┐
                 │       Intermediate Document Model           │
                 │ ─────────────────────────────────────────── │
                 │ • DocumentMetadata                          │
                 │ • Pages[] (width, height, rotation)         │
                 │   └── Elements[]:                           │
                 │       ├── TextElement (bbox, font, bold...) │
                 │       ├── ImageElement (bbox, bytes, fmt)   │
                 │       ├── TableElement (rows, cols, cells)  │
                 │       └── ShapeElement (type, bbox, stroke) │
                 │ • DocumentStyle                             │
                 └──────────────────────┬──────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │                 Exporters                 │
                  │  ├── DOCXExporter                         │
                  │  ├── PDFExporter                          │
                  │  ├── HTMLExporter                         │
                  │  ├── MarkdownExporter                     │
                  │  └── TXTExporter                          │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                           ┌─────────────────────────┐
                           │   Output Target File    │
                           └─────────────────────────┘
```

---

## 2. Cấu trúc Thư mục

```text
backend/
├── app/
│   ├── core/                  # Exceptions phân cấp & Logging bảo mật
│   │   ├── exceptions.py
│   │   └── logging.py
│   ├── models/                # Intermediate Document Model & Geometry
│   │   ├── geometry.py        # BoundingBox, IoU, scale, intersection
│   │   ├── elements.py        # TextElement, ImageElement, TableElement...
│   │   └── document.py        # Document, Page, DocumentMetadata...
│   ├── services/
│   │   ├── ocr/               # OCR provider interface (PaddleOCR, Tesseract)
│   │   │   ├── base.py
│   │   │   ├── paddle_provider.py
│   │   │   ├── tesseract_provider.py
│   │   │   └── ocr_service.py
│   │   ├── image/             # Image preprocessing (deskew, CLAHE, denoise)
│   │   │   └── preprocessor.py
│   │   ├── pdf/               # PyMuPDF service, text vs scan analyzer, merge, split
│   │   │   ├── analyzer.py
│   │   │   └── pdf_service.py
│   │   ├── docx/              # python-docx parser và exporter
│   │   │   └── docx_service.py
│   │   ├── document/          # DocumentLoader tự động nhận diện file type
│   │   │   └── loader.py
│   │   ├── converter/         # ConversionService điều phối toàn bộ luồng
│   │   │   └── converter_service.py
│   │   └── batch/             # BatchProcessor xử lý hàng loạt có progress callback
│   │       └── batch_processor.py
│   ├── exporters/             # Các Exporter ra TXT, MD, HTML, DOCX, PDF
│   ├── utils/                 # Nhận diện file type bằng Magic bytes
│   │   └── file_type.py
│   ├── config.py              # Cấu hình Pydantic tập trung
│   └── main.py                # Windows PowerShell CLI
├── tests/                     # Bộ kiểm thử pytest toàn diện (32 tests)
├── examples/                  # Script chạy thử demo.py
├── requirements.txt           # Danh mục dependencies
└── README.md
```

---

## 3. Hướng dẫn Cài đặt & Chạy trên Windows

### Bước 1: Tạo môi trường ảo (Virtual Environment)
Mở **Windows PowerShell** và chuyển vào thư mục `backend`:
```powershell
cd d:\Code\Tool-document\backend
python -m venv .venv
```

### Bước 2: Kích hoạt Virtual Environment trên PowerShell
Nếu gặp lỗi Execution Policy trên PowerShell, chạy lệnh kích hoạt an toàn:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Bước 3: Cài đặt Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 4: Chạy toàn bộ Test Suite (pytest)
```powershell
python -m pytest tests/ -v
```

---

## 4. Hướng dẫn Sử dụng CLI

Document Assistant cung cấp giao diện CLI trực quan, tối ưu cho Windows PowerShell:

### 1. Xem thông tin & phân tích tài liệu (info)
Tự động phát hiện loại file, số trang, kích thước, và phân tích PDF có text layer hay là trang scan:
```powershell
python -m app.main info document.pdf
python -m app.main info scan.png
python -m app.main info report.docx
```

### 2. Nhận dạng ký tự quang học (OCR)
Nhận diện văn bản tiếng Việt từ ảnh hoặc PDF scan:
```powershell
python -m app.main ocr document.png --lang vi
python -m app.main ocr scanned_page.jpg --output extracted.txt
```

### 3. Chuyển đổi định dạng (convert)
Chuyển đổi linh hoạt giữa PDF, DOCX, HTML, TXT, Markdown:
```powershell
# PDF sang Word (DOCX)
python -m app.main convert document.pdf --to docx

# PDF sang Text
python -m app.main convert document.pdf --to txt

# PDF sang HTML
python -m app.main convert document.pdf --to html

# Ảnh OCR sang Word (DOCX)
python -m app.main convert scan.jpg --to docx

# Ảnh sang PDF (Searchable PDF)
python -m app.main convert scan.png --to pdf
```

### 4. Gộp nhiều file PDF (merge)
```powershell
python -m app.main merge part1.pdf part2.pdf part3.pdf --output merged.pdf
```

### 5. Tách trang PDF (split)
```powershell
# Tách từng trang riêng lẻ:
python -m app.main split document.pdf

# Tách theo khoảng trang:
python -m app.main split document.pdf --pages "1-3, 5" --output-dir ./splits
```

---

## 5. Xử lý Lỗi PaddleOCR / PaddlePaddle trên Windows

- **Yêu cầu Visual C++ Redistributable**:
  PaddleOCR và OpenCV trên Windows yêu cầu **Microsoft Visual C++ Redistributable 2015-2022** (x64). Nếu chạy gặp lỗi `DLL load failed`, hãy tải và cài đặt bản cập nhật mới nhất từ trang chủ Microsoft.
- **Python 3.12 vs 3.13**:
  PaddlePaddle phiên bản chính thức phát hành trên PyPI hỗ trợ hoàn chỉnh Python 3.10 - 3.12 và bản cập nhật cho 3.13. Kiến trúc OCR của chúng tôi cung cấp **Provider Pattern**:
  - `PaddleOCRProvider` (Mặc định cho tiếng Việt chất lượng cao)
  - `TesseractOCRProvider` (Fallback offline thông dụng)
  - Kiến trúc mở rộng cho phép cắm bất kỳ Local AI OCR nào (ONNX runtime, v.v.) mà không thay đổi bất kỳ code nào ở Document Model hay Converter.
- **Tải model lần đầu**:
  Lần đầu chạy PaddleOCR, engine sẽ tự động tải weights model nhận diện tiếng Việt về thư mục `~/.paddleocr/`. Sau đó toàn bộ pipeline hoạt động hoàn toàn **100% OFFLINE**.

---

## 6. Giới hạn Kỹ thuật Thực tế (Realistic Limitations)

Tuân thủ tính trung thực kỹ thuật:
1. **Không đảm bảo 100% Pixel-Perfect layout khi chuyển PDF → DOCX**:
   File PDF lưu trữ văn bản theo toạ độ đồ họa tự do 2D ($X, Y$), trong khi DOCX tổ chức theo luồng văn bản (Flow Layout - Paragraphs, Tables, Sections). Engine đã tái tạo tối đa bằng cách gom nhóm dòng, phân tích heading, font size, bold/italic, alignment và table matrix, nhưng các văn bản đồ họa phức tạp (nhiều layer đè nhau) sẽ có sự xê dịch nhất định.
2. **DOCX → PDF trên môi trường thuần Python**:
   Việc render DOCX sang PDF chính xác chuẩn xác như Microsoft Word đòi hỏi MS Word engine (thông qua COM `win32com` trên Windows) hoặc LibreOffice headless. Khi chạy offline không phụ thuộc Microsoft Word/Office, backend sử dụng Document Model trung gian để vẽ lại cấu trúc cơ bản sang PDF.
3. **Bảng biểu phức tạp**:
   Bảng không có đường viền (borderless tables) hoặc bảng lồng nhau (nested tables) trong ảnh scan có thể cần module LayoutLM / Table Transformer chuyên sâu hơn ở giai đoạn AI tiếp theo.

---

## 7. Khả năng Mở rộng trong Tương lai (Future Extensibility)

Kiến trúc backend hiện tại đã sẵn sàng để tích hợp:
- **AI / LLM Integration**: Tóm tắt tài liệu, trích xuất thực thể (NER), hỏi đáp tài liệu thông qua interface chuẩn.
- **Template Văn bản Hành chính Việt Nam**: Kiểm tra thể thức văn bản theo Nghị định 30/2020/NĐ-CP.
- **Desktop UI**: Kết nối trực tiếp với Tauri hoặc PyQt/PySide thông qua IPC hoặc REST API.
- **Excel & PowerPoint**: Bổ sung `XLSXExporter` và `PPTXExporter` bằng cách implement `BaseExporter`.
