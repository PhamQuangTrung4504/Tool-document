# Document Assistant

Offline Windows Document & OCR Engine (Python 3.12+).

Toàn bộ mã nguồn Backend Engine nằm trong thư mục [`backend/`](file:///d:/Code/Tool-document/backend).

Vui lòng tham khảo chi tiết kiến trúc, hướng dẫn cài đặt và câu lệnh CLI tại:
**[Backend Documentation](file:///d:/Code/Tool-document/backend/README.md)**.

## Quick Start on Windows PowerShell:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest tests/ -v
python examples/demo.py
```
