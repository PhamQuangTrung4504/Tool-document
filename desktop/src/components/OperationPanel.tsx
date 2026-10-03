import React from "react";
import { Play, Folder } from "lucide-react";
import { OperationType, OCRMode, OutputFormat } from "../types/ipc";
import { getFileExtension, getFileParentDir } from "../utils/fileUtils";
import { tauriIpc } from "../services/tauriIpc";

interface OperationPanelProps {
  selectedFile: string;
  operation: OperationType;
  ocrMode: OCRMode;
  outputFormat: OutputFormat;
  outputDir?: string | null;
  onChangeOperation: (op: OperationType) => void;
  onChangeOcrMode: (mode: OCRMode) => void;
  onChangeOutputFormat: (fmt: OutputFormat) => void;
  onChangeOutputDir?: (dir: string | null) => void;
  onStart: () => void;
  isProcessing: boolean;
}

export const OperationPanel: React.FC<OperationPanelProps> = ({
  selectedFile,
  operation,
  ocrMode,
  outputFormat,
  outputDir,
  onChangeOperation,
  onChangeOcrMode,
  onChangeOutputFormat,
  onChangeOutputDir,
  onStart,
  isProcessing,
}) => {
  const ext = getFileExtension(selectedFile);
  const isPdf = ext === "pdf";
  const isDocx = ext === "docx";
  const isImage = ["png", "jpg", "jpeg", "bmp", "tiff"].includes(ext);

  // Available output formats depending on input
  const getAvailableFormats = (): { id: OutputFormat; label: string }[] => {
    if (isDocx) {
      return [
        { id: "pdf", label: "PDF" },
        { id: "html", label: "HTML" },
        { id: "txt", label: "TXT" },
        { id: "md", label: "Markdown" },
      ];
    }
    if (isPdf) {
      return [
        { id: "docx", label: "DOCX" },
        { id: "html", label: "HTML" },
        { id: "txt", label: "TXT" },
        { id: "md", label: "Markdown" },
      ];
    }
    if (isImage) {
      return [
        { id: "docx", label: "DOCX" },
        { id: "pdf", label: "PDF" },
        { id: "html", label: "HTML" },
        { id: "txt", label: "TXT" },
        { id: "md", label: "Markdown" },
      ];
    }
    if (ext === "txt") {
      return [
        { id: "docx", label: "DOCX" },
        { id: "pdf", label: "PDF" },
        { id: "html", label: "HTML" },
        { id: "md", label: "Markdown" },
      ];
    }
    if (ext === "md") {
      return [
        { id: "docx", label: "DOCX" },
        { id: "pdf", label: "PDF" },
        { id: "html", label: "HTML" },
        { id: "txt", label: "TXT" },
      ];
    }
    if (ext === "html" || ext === "htm") {
      return [
        { id: "docx", label: "DOCX" },
        { id: "pdf", label: "PDF" },
        { id: "txt", label: "TXT" },
        { id: "md", label: "Markdown" },
      ];
    }
    return [
      { id: "docx", label: "DOCX" },
      { id: "pdf", label: "PDF" },
      { id: "html", label: "HTML" },
      { id: "txt", label: "TXT" },
      { id: "md", label: "Markdown" },
    ];
  };

  const availableFormats = getAvailableFormats();

  React.useEffect(() => {
    if (availableFormats.length > 0 && !availableFormats.some((f) => f.id === outputFormat)) {
      onChangeOutputFormat(availableFormats[0].id);
    }
  }, [selectedFile, operation]);

  const handlePickOutputDir = async () => {
    try {
      const folder = await tauriIpc.pickFolder();
      if (folder) {
        onChangeOutputDir?.(folder);
      }
    } catch (err) {
      console.error("Error picking output directory:", err);
    }
  };

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ fontSize: "16px", fontWeight: 600 }}>Tùy chọn xử lý</h3>
        <div style={{ fontSize: "13px", color: "var(--text-muted)" }}>
          Định dạng gốc: <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{ext.toUpperCase()}</span>
        </div>
      </div>

      {/* Operation Selection */}
      <div className="option-section">
        <label className="option-label">Thao tác</label>
        <div className="radio-group">
          <button
            type="button"
            className={`radio-btn op-btn ${operation === "convert" ? "active op-convert-active" : ""}`}
            onClick={() => onChangeOperation("convert")}
          >
            <span
              style={{
                display: "inline-block",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: operation === "convert" ? "var(--accent-primary)" : "var(--border-strong)",
              }}
            />
            <span>Chuyển đổi (Convert)</span>
          </button>
          <button
            type="button"
            className={`radio-btn op-btn ${operation === "ocr" ? "active op-ocr-active" : ""}`}
            onClick={() => onChangeOperation("ocr")}
          >
            <span
              style={{
                display: "inline-block",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: operation === "ocr" ? "#d97706" : "var(--border-strong)",
              }}
            />
            <span>Nhận diện (OCR)</span>
          </button>
          {isPdf && (
            <button
              type="button"
              className={`radio-btn op-btn ${operation === "split" ? "active op-split-active" : ""}`}
              onClick={() => onChangeOperation("split")}
            >
              <span
                style={{
                  display: "inline-block",
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  backgroundColor: operation === "split" ? "#9333ea" : "var(--border-strong)",
                }}
              />
              <span>Tách PDF (Split)</span>
            </button>
          )}
        </div>
      </div>

      {/* Output Format (when Convert) */}
      {operation === "convert" && (
        <div className="option-section">
          <label className="option-label">Định dạng đầu ra</label>
          <div className="radio-group">
            {availableFormats.map((fmt) => (
              <button
                key={fmt.id}
                type="button"
                className={`radio-btn ${outputFormat === fmt.id ? "active" : ""}`}
                onClick={() => onChangeOutputFormat(fmt.id)}
              >
                {fmt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* OCR Mode (when OCR or Convert on PDF/Images) */}
      {(operation === "ocr" || (operation === "convert" && (isPdf || isImage))) && (
        <div className="option-section">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <label className="option-label">Chế độ OCR</label>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
              {ocrMode === "fast" && "Tốc độ nhanh (~4.5s/trang)"}
              {ocrMode === "full" && "Đầy đủ & Nhận diện bảng (~5.7s/trang)"}
              {ocrMode === "auto" && "Tự động phân tích tối ưu"}
            </span>
          </div>
          <div className="radio-group">
            <button
              type="button"
              className={`radio-btn ${ocrMode === "auto" ? "active" : ""}`}
              onClick={() => onChangeOcrMode("auto")}
            >
              Auto (Mặc định)
            </button>
            <button
              type="button"
              className={`radio-btn ${ocrMode === "fast" ? "active" : ""}`}
              onClick={() => onChangeOcrMode("fast")}
            >
              Fast (Nhanh)
            </button>
            <button
              type="button"
              className={`radio-btn ${ocrMode === "full" ? "active" : ""}`}
              onClick={() => onChangeOcrMode("full")}
            >
              Full (Đầy đủ)
            </button>
          </div>
        </div>
      )}

      {/* Destination Directory (Địa chỉ lưu) */}
      <div className="option-section">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <label className="option-label">Địa chỉ lưu file</label>
          {outputDir && (
            <button
              type="button"
              style={{
                background: "none",
                border: "none",
                color: "var(--accent-primary)",
                fontSize: "12px",
                cursor: "pointer",
                fontWeight: 500,
              }}
              onClick={() => onChangeOutputDir?.(null)}
            >
              Đặt lại mặc định
            </button>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div
            style={{
              flex: 1,
              padding: "8px 12px",
              backgroundColor: "var(--bg-primary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              fontSize: "12.5px",
              color: outputDir ? "var(--text-primary)" : "var(--text-muted)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={outputDir || (selectedFile ? getFileParentDir(selectedFile) : "Cùng thư mục file gốc")}
          >
            📁 {outputDir || (selectedFile ? `Mặc định: ${getFileParentDir(selectedFile)}` : "Cùng thư mục file gốc")}
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: "8px 14px", fontSize: "12.5px", whiteSpace: "nowrap", display: "flex", alignItems: "center", gap: "6px" }}
            onClick={handlePickOutputDir}
          >
            <Folder size={14} />
            <span>Chọn nơi lưu...</span>
          </button>
        </div>
      </div>

      {/* Action Button */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "8px" }}>
        <button
          type="button"
          className="btn btn-primary"
          style={{ padding: "10px 24px", fontSize: "14px", fontWeight: 600 }}
          disabled={isProcessing}
          onClick={onStart}
        >
          <Play size={16} fill="currentColor" />
          <span>Bắt đầu xử lý</span>
        </button>
      </div>
    </div>
  );
};
