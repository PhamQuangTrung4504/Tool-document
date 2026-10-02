import React from "react";
import { Play } from "lucide-react";
import { OperationType, OCRMode, OutputFormat } from "../types/ipc";
import { getFileExtension } from "../utils/fileUtils";

interface OperationPanelProps {
  selectedFile: string;
  operation: OperationType;
  ocrMode: OCRMode;
  outputFormat: OutputFormat;
  onChangeOperation: (op: OperationType) => void;
  onChangeOcrMode: (mode: OCRMode) => void;
  onChangeOutputFormat: (fmt: OutputFormat) => void;
  onStart: () => void;
  isProcessing: boolean;
}

export const OperationPanel: React.FC<OperationPanelProps> = ({
  selectedFile,
  operation,
  ocrMode,
  outputFormat,
  onChangeOperation,
  onChangeOcrMode,
  onChangeOutputFormat,
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
        { id: "txt", label: "TXT" },
        { id: "md", label: "Markdown" },
        { id: "html", label: "HTML" },
      ];
    }
    if (isPdf) {
      return [
        { id: "docx", label: "DOCX" },
        { id: "txt", label: "TXT" },
        { id: "md", label: "Markdown" },
        { id: "html", label: "HTML" },
      ];
    }
    if (isImage) {
      return [
        { id: "docx", label: "DOCX" },
        { id: "pdf", label: "PDF" },
        { id: "txt", label: "TXT" },
        { id: "md", label: "Markdown" },
        { id: "html", label: "HTML" },
      ];
    }
    return [
      { id: "docx", label: "DOCX" },
      { id: "pdf", label: "PDF" },
      { id: "txt", label: "TXT" },
    ];
  };

  const availableFormats = getAvailableFormats();

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
            className={`radio-btn ${operation === "convert" ? "active" : ""}`}
            onClick={() => onChangeOperation("convert")}
          >
            Chuyển đổi (Convert)
          </button>
          <button
            type="button"
            className={`radio-btn ${operation === "ocr" ? "active" : ""}`}
            onClick={() => onChangeOperation("ocr")}
          >
            Nhận diện (OCR)
          </button>
          {isPdf && (
            <>
              <button
                type="button"
                className={`radio-btn ${operation === "split" ? "active" : ""}`}
                onClick={() => onChangeOperation("split")}
              >
                Tách PDF (Split)
              </button>
            </>
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
