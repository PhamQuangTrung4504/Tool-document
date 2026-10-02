# Document Assistant Desktop (Tauri 2 + React + TypeScript)

Ứng dụng Windows Desktop cho hệ thống **Document Assistant**, xử lý và chuyển đổi tài liệu hoàn toàn cục bộ (offline) trên máy tính bằng Tauri 2, React, TypeScript, Vite và backend Python engine qua cơ chế stdin/stdout IPC.

## Kiến trúc hệ thống

```
React Desktop UI (Vite / TypeScript)
       │
       ▼ (Tauri IPC commands: execute_ipc, cancel_operation, etc.)
Rust Core Layer (src-tauri)
       │
       ▼ (Standard I/O JSON IPC: python -m app.main ipc --stdin)
Python Backend Engine (Document Assistant)
       │
       ├── OCR Service (PaddleOCR Offline CPU)
       ├── PDF Engine (PyMuPDF / pdfplumber)
       ├── DOCX Engine (python-docx)
       └── Exporters (DOCX, PDF, TXT, HTML, Markdown)
```

## Yêu cầu môi trường

- **Node.js**: v18+ (khuyên dùng Node 22+)
- **Rust**: 1.78+ (`stable-x86_64-pc-windows-gnu` hoặc `stable-x86_64-pc-windows-msvc`)
- **Python**: 3.10+ (với các thư viện trong `backend/requirements.txt`)

## Hướng dẫn phát triển và chạy ứng dụng

### 1. Cài đặt dependencies frontend
```powershell
cd desktop
npm install
```

### 2. Chạy ứng dụng chế độ Development
```powershell
cd desktop
npm run tauri dev
```

### 3. Build ứng dụng sản phẩm (Production Windows Binary)
```powershell
cd desktop
npm run tauri build
```
File thực thi `.exe` sẽ được tạo tại:
`desktop/src-tauri/target/release/document-assistant-desktop.exe`

### 4. Chạy kiểm thử tự động Desktop
```powershell
cd desktop
node tests/desktop_integration.mjs
```

## Cấu trúc thư mục

```
desktop/
├── src/
│   ├── components/
│   │   ├── DocumentPreview.tsx
│   │   ├── FileCard.tsx
│   │   ├── FileDropzone.tsx
│   │   ├── OperationPanel.tsx
│   │   ├── ProgressModal.tsx
│   │   ├── ResultCard.tsx
│   │   └── Sidebar.tsx
│   ├── pages/
│   │   ├── ConvertPage.tsx
│   │   ├── HistoryPage.tsx
│   │   ├── HomePage.tsx
│   │   ├── MergePage.tsx
│   │   ├── OCRPage.tsx
│   │   ├── SettingsPage.tsx
│   │   └── SplitPage.tsx
│   ├── services/
│   │   ├── historyService.ts
│   │   └── tauriIpc.ts
│   ├── styles/
│   │   └── index.css
│   ├── types/
│   │   ├── history.ts
│   │   └── ipc.ts
│   ├── utils/
│   │   └── fileUtils.ts
│   ├── App.tsx
│   └── main.tsx
├── src-tauri/
│   ├── capabilities/
│   │   └── default.json
│   ├── src/
│   │   ├── commands.rs
│   │   ├── lib.rs
│   │   ├── main.rs
│   │   └── python_engine.rs
│   ├── build.rs
│   ├── Cargo.toml
│   └── tauri.conf.json
├── tests/
│   └── desktop_integration.mjs
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```
