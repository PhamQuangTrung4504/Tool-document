# 📄 Document Assistant — Offline Windows Document & OCR Engine

> **Ứng dụng Windows Desktop & Backend Engine xử lý tài liệu, OCR tiếng Việt và chuyển đổi định dạng 100% OFFLINE trên Windows.**
>
> 🚀 Xây dựng với **Tauri 2 + React + TypeScript + Tailwind CSS** và **Python Core Engine (PyMuPDF, PaddleOCR, python-docx)**.

---

## 📑 Mục lục
1. [Giới thiệu tổng quan](#1-giới-thiệu-tổng-quan)
2. [Yêu cầu hệ thống](#2-yêu-cầu-hệ-thống)
3. [Cài đặt môi trường nhanh (Quick Setup)](#3-cài-đặt-môi-trường-nhanh-quick-setup)
4. [Hướng dẫn Chạy ứng dụng](#4-hướng-dẫn-chạy-ứng-dụng)
   - [Cách 1: Chạy ứng dụng Desktop (Khuyên dùng)](#cách-1-chạy-ứng-dụng-desktop-gui-khuyên-dùng)
   - [Cách 2: Chạy giao diện Web trên trình duyệt](#cách-2-chạy-giao-diện-web-trên-trình-duyệt)
   - [Cách 3: Chạy trực tiếp qua PowerShell CLI](#cách-3-chạy-trực-tiếp-qua-powershell-cli)
5. [Hướng dẫn sử dụng chi tiết các tính năng](#5-hướng-dẫn-sử-dụng-chi-tiết-các-tính-năng)
   - [1. Chuyển đổi định dạng tài liệu (Convert)](#1-chuyển-đổi-định-dạng-tài-liệu-convert)
   - [2. Nhận dạng chữ tiếng Việt (OCR Tiếng Việt)](#2-nhận-dạng-chữ-tiếng-việt-ocr-tiếng-việt)
   - [3. Gộp nhiều file PDF (Merge PDF)](#3-gộp-nhiều-file-pdf-merge-pdf)
   - [4. Tách trang PDF (Split PDF)](#4-tách-trang-pdf-split-pdf)
   - [5. Lịch sử tác vụ (History)](#5-lịch-sử-tác-vụ-history)
   - [6. Cấu hình & Trạng thái Backend (Settings)](#6-cấu-hình--trạng-thái-backend-settings)
6. [Hướng dẫn câu lệnh CLI Backend](#6-hướng-dẫn-câu-lệnh-cli-backend)
7. [Kiểm tra & Xác minh hoạt động (Verification & Testing)](#7-kiểm-tra--xác-minh-hoạt-động-verification--testing)
8. [Xử lý sự cố thường gặp (Troubleshooting)](#8-xử-lý-sự-cố-thường-gặp-troubleshooting)

---

## 1. Giới thiệu tổng quan

**Document Assistant** giải quyết trọn vẹn nhu cầu xử lý tài liệu bảo mật văn phòng:
- **100% Offline & Bảo mật**: Không gửi tài liệu ra ngoài internet, dữ liệu xử lý trực tiếp trên CPU/RAM máy tính.
- **OCR Tiếng Việt chuẩn xác**: Tích hợp sẵn PaddleOCR tiếng Việt với khả năng tự động nắn thẳng ảnh (deskew), tăng độ tương phản và lọc nhiễu.
- **Mô hình tài liệu trung gian (Intermediate Document Model)**: Tái tạo cấu trúc bảng biểu, chia cột, định dạng phông chữ, tiêu đề khi chuyển đổi.
- **Hỗ trợ đa định dạng**: PDF, DOCX, PNG, JPG, BMP, TIFF, TXT, HTML, Markdown.

```
┌────────────────────────────────────────────────────────┐
│     Desktop UI (Tauri 2 + React 18 + TypeScript)       │
└───────────────────────────┬────────────────────────────┘
                            │ Standard I/O IPC (JSON)
┌───────────────────────────▼────────────────────────────┐
│      Python Backend Core Engine (Fast & Resilient)     │
│  ├── OCR Service (PaddleOCR Tiếng Việt Offline)        │
│  ├── PDF Engine (PyMuPDF - Phân tích Layout / Text)    │
│  ├── DOCX Engine (python-docx - Đoạn văn, bảng biểu)   │
│  └── Multi-format Exporters (DOCX, PDF, HTML, MD, TXT) │
└────────────────────────────────────────────────────────┘
```

---

## 2. Yêu cầu hệ thống

Trước khi chạy, hãy đảm bảo máy tính đã cài đặt:
- **Hệ điều hành**: Windows 10 hoặc Windows 11 (64-bit).
- **Python**: Phiên bản `3.10` đến `3.13` (Khuyên dùng Python 3.12 hoặc 3.13 đã tích hợp sẵn trong PATH).
- **Node.js**: Phiên bản `18.x` trở lên (Khuyên dùng Node 20+ hoặc 22+).
- **Rust & Cargo**: Bắt buộc nếu chạy `npm run tauri dev` hoặc build `.exe` (Cài đặt tại [rustup.rs](https://rustup.rs/)).
- **Microsoft Visual C++ Redistributable (2015-2022 x64)**: Thư viện runtime cần thiết cho PaddleOCR và OpenCV trên Windows.

---

## 3. Cài đặt môi trường nhanh (Quick Setup)

Mở **Windows PowerShell** và chạy lần lượt các bước sau:

### Bước 1: Cài đặt thư viện Backend (Python)
```powershell
cd d:\Code\Tool-document\backend

# Tạo môi trường ảo (nếu chưa có):
python -m venv .venv

# Kích hoạt venv (nếu PowerShell báo lỗi Execution Policy, xem mục 8):
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

# Cài đặt toàn bộ dependencies:
pip install -r requirements.txt
```

> **Lưu ý**: Nếu máy tính đã có sẵn các package trong Python hệ thống (`pymupdf`, `paddleocr`, `pydantic`, `python-docx`), bạn có thể bỏ qua việc tạo venv và chạy trực tiếp.

### Bước 2: Cài đặt thư viện Frontend (Desktop)
```powershell
cd d:\Code\Tool-document\desktop
npm install
```

---

## 4. Hướng dẫn Chạy ứng dụng

Bạn có 3 lựa chọn để chạy và kiểm tra ứng dụng:

### Cách 1: Chạy ứng dụng Desktop GUI (Khuyên dùng)
Chạy ứng dụng dưới dạng cửa sổ phần mềm Windows hoàn chỉnh thông qua Tauri:

```powershell
cd d:\Code\Tool-document\desktop
npm run tauri dev
```
- Quá trình biên dịch Rust và Vite sẽ khởi động.
- Cửa sổ ứng dụng **Document Assistant** sẽ tự động mở lên trên màn hình Windows.
- Backend Python sẽ được tự động kích hoạt ngầm qua cơ chế Standard I/O IPC.

---

### Cách 2: Chạy giao diện Web trên trình duyệt
Nếu bạn muốn kiểm tra nhanh giao diện người dùng trên trình duyệt (Chrome/Edge):

```powershell
cd d:\Code\Tool-document\desktop
npm run dev
```
- Mở trình duyệt và truy cập: `http://localhost:1420` (hoặc cổng hiển thị trên terminal).
- Bạn có thể thao tác với toàn bộ giao diện, xem trước tài liệu, lịch sử và cài đặt.

---

### Cách 3: Chạy trực tiếp qua PowerShell CLI
Bạn có thể gọi trực tiếp Backend Engine thông qua dòng lệnh mà không cần mở giao diện đồ họa:

```powershell
cd d:\Code\Tool-document\backend
python -m app.main --help
```

---

## 5. Hướng dẫn sử dụng chi tiết các tính năng

### 1. Chuyển đổi định dạng tài liệu (Convert)
- **Truy cập**: Nhấp vào mục **"Chuyển đổi"** (biểu tượng mũi tên đảo chiều) ở thanh điều hướng bên trái.
- **Thao tác**:
  1. Kéo thả file tài liệu (PDF, Word DOCX, hoặc Ảnh JPG/PNG) vào khung tải lên hoặc nhấp để chọn file.
  2. Xem trước thông tin tài liệu (Số trang, dung lượng, định dạng phát hiện).
  3. Chọn định dạng xuất ra:
     - **DOCX**: Giữ cấu trúc đoạn văn bản, bảng biểu, phông chữ.
     - **PDF**: Tạo tài liệu PDF có thể tìm kiếm văn bản (Searchable PDF).
     - **HTML / Markdown**: Xuất nội dung web/markdown phục vụ lưu trữ.
     - **TXT**: Trích xuất thuần văn bản thô.
  4. Nếu tài liệu là PDF dạng scan hoặc ảnh, bật tuỳ chọn **"Buộc chạy OCR"** (Force OCR) và chọn ngôn ngữ (Mặc định: Tiếng Việt).
  5. Bấm nút **"Bắt đầu chuyển đổi"**. Thanh tiến trình sẽ hiển thị phần trăm xử lý.
  6. Khi hoàn tất, bấm **"Mở file"** để xem ngay hoặc **"Mở thư mục"** để xem vị trí lưu file.

---

### 2. Nhận dạng chữ tiếng Việt (OCR Tiếng Việt)
- **Truy cập**: Nhấp vào mục **"OCR Tiếng Việt"** (biểu tượng quét văn bản).
- **Thao tác**:
  1. Tải ảnh tài liệu (hóa đơn, chứng từ, văn bản scan, bằng lái, CMND/CCCD...).
  2. Chọn chế độ OCR:
     - **Nhanh (Fast)**: Tối ưu tốc độ xử lý nhanh trên CPU thông thường.
     - **Cân bằng (Balanced)**: Tự động tiền xử lý nắn thẳng ảnh (deskew) và khử nhiễu.
     - **Chính xác (Accurate)**: Phân tích sâu từng khối văn bản tiếng Việt có dấu.
  3. Bấm **"Bắt đầu nhận dạng OCR"**.
  4. Kết quả nhận dạng sẽ hiển thị ở khung bên phải:
     - Bấm **"Sao chép văn bản"** để copy toàn bộ nội dung vào Clipboard.
     - Bấm **"Lưu file kết quả"** để lưu thành file `.txt` hoặc `.docx`.

---

### 3. Gộp nhiều file PDF (Merge PDF)
- **Truy cập**: Nhấp vào mục **"Gộp PDF"** (biểu tượng ghép file).
- **Thao tác**:
  1. Kéo thả nhiều file PDF vào danh sách (ví dụ: `Chuong1.pdf`, `Chuong2.pdf`, `PhuLuc.pdf`).
  2. Dùng các nút mũi tên lên/xuống để sắp xếp đúng thứ tự các file cần gộp.
  3. Đặt tên file xuất ra (Mặc định: `tai_lieu_gop.pdf`).
  4. Bấm **"Gộp tài liệu"**. File PDF tổng hợp sẽ được tạo với nguyên vẹn trang và chất lượng gốc.

---

### 4. Tách trang PDF (Split PDF)
- **Truy cập**: Nhấp vào mục **"Tách PDF"** (biểu tượng chia cắt).
- **Thao tác**:
  1. Chọn file PDF nguồn cần tách.
  2. Chọn phương thức tách:
     - **Tách tất cả trang**: Mỗi trang sẽ thành 1 file PDF độc lập.
     - **Tách theo khoảng tuỳ chọn**: Nhập dải trang mong muốn, ví dụ:
       - `1-3`: Trích xuất từ trang 1 đến trang 3 thành 1 file.
       - `1-3, 5, 8-10`: Trích xuất thành các phần tương ứng.
  3. Bấm **"Thực hiện tách PDF"**. Các file kết quả sẽ được lưu vào thư mục con cùng tên.

---

### 5. Lịch sử tác vụ (History)
- **Truy cập**: Nhấp vào mục **"Lịch sử"** (biểu tượng đồng hồ).
- Quản lý danh sách các lượt xử lý gần nhất:
  - Tên file nguồn, định dạng đích, trạng thái (Thành công / Đang xử lý / Thất bại).
  - Thời gian thực hiện và thời gian xử lý (giây).
  - Nút **Mở file** trực tiếp và nút **Mở thư mục chứa** tiện lợi.
  - Nút **Xóa lịch sử** để dọn dẹp danh sách khi cần.

---

### 6. Cấu hình & Trạng thái Backend (Settings)
- **Truy cập**: Nhấp vào mục **"Cài đặt"** (biểu tượng bánh răng).
- **Tính năng**:
  - Xem trạng thái kết nối với Python Backend Engine (`Sẵn sàng` / `Mất kết nối`).
  - Đường dẫn môi trường Python hiện đang thực thi.
  - Nút **"Kiểm tra sức khỏe Backend"** (Ping Health Check) để kiểm tra độ trễ phản hồi.

---

## 6. Hướng dẫn câu lệnh CLI Backend

Dành cho người dùng kỹ thuật hoặc tích hợp tự động qua script PowerShell:

```powershell
cd d:\Code\Tool-document\backend
```

### 1. Xem thông tin & phân tích cấu trúc tài liệu (`info`)
Kiểm tra số trang, loại PDF (có text layer hay là scan hoàn toàn), bảng biểu, kích thước:
```powershell
python -m app.main info document.pdf
python -m app.main info hoa_don.jpg
```

### 2. Nhận dạng ký tự quang học (`ocr`)
Trích xuất chữ tiếng Việt từ ảnh hoặc PDF scan:
```powershell
# In trực tiếp kết quả ra màn hình:
python -m app.main ocr scan_doc.png --lang vi

# Lưu kết quả OCR ra file text:
python -m app.main ocr scan_doc.png -o ket_qua.txt --lang vi
```

### 3. Chuyển đổi định dạng (`convert`)
```powershell
# Chuyển PDF sang Word (.docx):
python -m app.main convert report.pdf --to docx

# Chuyển PDF scan sang Word có bật OCR:
python -m app.main convert scan_book.pdf --to docx --force-ocr --lang vi

# Chuyển ảnh scan sang file PDF có thể bôi đen tìm kiếm (Searchable PDF):
python -m app.main convert giay_to.png --to pdf

# Chuyển PDF sang Markdown hoặc HTML:
python -m app.main convert document.pdf --to md
python -m app.main convert document.pdf --to html
```

### 4. Gộp nhiều file PDF (`merge`)
```powershell
python -m app.main merge tap1.pdf tap2.pdf tap3.pdf -o tap_tong_hop.pdf
```

### 5. Tách trang PDF (`split`)
```powershell
# Tách từng trang rời rạc:
python -m app.main split tailieu.pdf

# Tách theo khoảng trang cụ thể:
python -m app.main split tailieu.pdf --pages "1-5, 8" -o ./splits
```

---

## 7. Kiểm tra & Xác minh hoạt động (Verification & Testing)

Hệ thống đã được thiết kế và kiểm thử với các bộ test tự động:

### 1. Kiểm thử trọn vẹn Backend (pytest — 55/55 Tests PASSED)
Kiểm tra Document Model, PaddleOCR tiếng Việt, PyMuPDF, DOCX parsing, Error Handling:
```powershell
cd d:\Code\Tool-document\backend
python -m pytest tests/ -v
```

### 2. Chạy Demo mẫu Backend tự động
Tự động tạo tài liệu mẫu chứa văn bản tiếng Việt + bảng biểu, xuất ra 5 định dạng (`docx`, `pdf`, `html`, `md`, `txt`) và test merge/split:
```powershell
cd d:\Code\Tool-document\backend
python examples/demo.py
```

### 3. Kiểm thử tích hợp Desktop IPC (15/15 Tests PASSED)
Kiểm tra liên kết Rust IPC, giao tiếp JSON với Python, xử lý đường dẫn tiếng Việt và lịch sử tác vụ:
```powershell
cd d:\Code\Tool-document\desktop
node tests/desktop_integration.mjs
```

---

## 8. Xử lý sự cố thường gặp (Troubleshooting)

### 1. Lỗi PowerShell không cho kích hoạt venv (`Activate.ps1 cannot be loaded`)
- **Nguyên nhân**: Chính sách bảo mật ExecutionPolicy mặc định của PowerShell trên Windows.
- **Khắc phục**: Chạy lệnh sau trong PowerShell trước khi kích hoạt venv:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\.venv\Scripts\Activate.ps1
  ```

### 2. Lỗi `DLL load failed` khi nạp PaddleOCR hoặc OpenCV
- **Nguyên nhân**: Thiếu bộ thư viện C++ runtime của Microsoft trên Windows.
- **Khắc phục**: Tải và cài đặt miễn phí gói **Microsoft Visual C++ Redistributable 2015-2022 (x64)** từ trang chính thức của Microsoft, sau đó khởi động lại terminal.

### 3. Lần đầu chạy OCR tiếng Việt phản hồi hơi chậm
- **Nguyên nhân**: Ở lần chạy đầu tiên, PaddleOCR sẽ tự động tải các model trọng số tiếng Việt (~15 MB) về thư mục `C:\Users\<Tên_User>\.paddleocr\`.
- **Khắc phục**: Chờ khoảng 15-30 giây cho lần đầu tiên. Từ các lần tiếp theo, hệ thống sẽ chạy **hoàn toàn 100% OFFLINE** với tốc độ cực nhanh.

### 4. Không tìm thấy đường dẫn Python trong ứng dụng Desktop
- **Nguyên nhân**: Python chưa được thêm vào biến môi trường `PATH`.
- **Khắc phục**: Bạn có thể đặt biến môi trường chỉ định đường dẫn trực tiếp:
  ```powershell
  [System.Environment]::SetEnvironmentVariable('DOC_ASSISTANT_PYTHON', 'C:\Users\pqtru\AppData\Local\Programs\Python\Python313\python.exe', 'User')
  ```
  Hoặc thiết lập thư mục virtual environment chuẩn tại: `d:\Code\Tool-document\backend\.venv`.

---

## 👨‍💻 Cấu trúc mã nguồn (Project Structure)

```text
Tool-document/
├── README.md                      # Hướng dẫn sử dụng & vận hành tổng thể (File này)
├── backend/                       # Engine Python xử lý tài liệu & OCR
│   ├── app/
│   │   ├── core/                  # Xử lý IPC, Logging an toàn, Exceptions phân cấp
│   │   ├── models/                # Document Model trung gian, BoundingBox, Elements
│   │   ├── services/              # Dịch vụ OCR, PDF, DOCX, Preprocessing, Converter
│   │   ├── exporters/             # Xuất file ra DOCX, PDF, HTML, Markdown, TXT
│   │   └── main.py                # Điểm vào CLI & Standard I/O IPC
│   ├── tests/                     # Bộ kiểm thử pytest (55 unit & integration tests)
│   ├── examples/                  # Mã nguồn kịch bản chạy thử (demo.py)
│   ├── requirements.txt           # Danh mục dependencies Python
│   └── README.md                  # Tài liệu kiến trúc chuyên sâu Backend
│
└── desktop/                       # Ứng dụng Windows Desktop (Tauri 2 + React)
    ├── src/                       # Giao diện React, TypeScript & Tailwind CSS
    │   ├── components/            # Sidebar, FileDropzone, ResultCard, Modal...
    │   ├── pages/                 # ConvertPage, OCRPage, MergePage, SplitPage...
    │   └── services/              # Gọi Tauri IPC & Quản lý lịch sử tác vụ
    ├── src-tauri/                 # Rust Core Layer điều phối Windows Process & IPC
    │   ├── src/lib.rs             # Định nghĩa lệnh Tauri commands
    │   └── src/python_engine.rs   # Bộ dò tìm Python & quản lý tiến trình ngầm
    ├── tests/                     # Bộ kiểm thử tích hợp Desktop (15/15 tests)
    ├── package.json               # Cấu hình dự án Node.js / Vite
    └── README.md                  # Hướng dẫn phát triển Desktop
```

---
*Chúc bạn có trải nghiệm làm việc hiệu quả với **Document Assistant**!*
