import React from "react";
import { CheckCircle2, Folder, ExternalLink, RefreshCw, AlertTriangle } from "lucide-react";
import { IPCResponse } from "../types/ipc";
import { getFileName, formatDuration } from "../utils/fileUtils";
import { tauriIpc } from "../services/tauriIpc";

interface ResultCardProps {
  inputPath: string;
  response: IPCResponse;
  onReset: () => void;
}

export const ResultCard: React.FC<ResultCardProps> = ({
  inputPath,
  response,
  onReset,
}) => {
  const inputName = getFileName(inputPath);
  const outputPath =
    typeof response.output === "string"
      ? response.output
      : Array.isArray(response.output)
      ? response.output.join(", ")
      : "";
  const outputName = outputPath ? getFileName(outputPath) : "Nội dung trích xuất";

  const handleOpenFile = async () => {
    if (outputPath) {
      try {
        await tauriIpc.openFile(outputPath);
      } catch (e) {
        console.error("Failed to open file:", e);
      }
    }
  };

  const handleOpenFolder = async () => {
    if (outputPath) {
      try {
        await tauriIpc.openFolder(outputPath);
      } catch (e) {
        console.error("Failed to open folder:", e);
      }
    }
  };

  const metrics = response.metrics || {};
  const warnings = response.warnings || [];

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <CheckCircle2 size={28} style={{ color: "var(--status-success-text)" }} />
        <div>
          <h3 style={{ fontSize: "18px", fontWeight: 700, color: "var(--status-success-text)" }}>
            Hoàn tất thành công
          </h3>
          <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            Tài liệu đã được xử lý và xuất ra ổ đĩa
          </p>
        </div>
      </div>

      {/* File transformation summary */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          padding: "14px 16px",
          backgroundColor: "var(--bg-primary)",
          borderRadius: "var(--radius-md)",
          fontSize: "14px",
          fontWeight: 600,
        }}
      >
        <span style={{ color: "var(--text-secondary)" }}>{inputName}</span>
        <span style={{ color: "var(--accent-primary)" }}>→</span>
        <span style={{ color: "var(--text-primary)" }}>{outputName}</span>
      </div>

      {/* Metrics Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
          gap: "12px",
        }}
      >
        {metrics.pages !== undefined && (
          <div
            style={{
              padding: "12px",
              backgroundColor: "var(--bg-primary)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Số trang</div>
            <div style={{ fontSize: "16px", fontWeight: 700, marginTop: "2px" }}>
              {metrics.pages}
            </div>
          </div>
        )}
        <div
          style={{
            padding: "12px",
            backgroundColor: "var(--bg-primary)",
            borderRadius: "var(--radius-md)",
          }}
        >
          <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Thời gian xử lý</div>
          <div style={{ fontSize: "16px", fontWeight: 700, marginTop: "2px" }}>
            {formatDuration(metrics.processing_time_ms)}
          </div>
        </div>
        {metrics.ocr_mode && (
          <div
            style={{
              padding: "12px",
              backgroundColor: "var(--bg-primary)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Chế độ OCR</div>
            <div
              style={{
                fontSize: "16px",
                fontWeight: 700,
                marginTop: "2px",
                textTransform: "uppercase",
              }}
            >
              {metrics.ocr_mode}
            </div>
          </div>
        )}
        {metrics.text_coverage !== undefined && (
          <div
            style={{
              padding: "12px",
              backgroundColor: "var(--bg-primary)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Độ phủ văn bản</div>
            <div style={{ fontSize: "16px", fontWeight: 700, marginTop: "2px" }}>
              {(metrics.text_coverage * 100).toFixed(1)}%
            </div>
          </div>
        )}
      </div>

      {/* Warnings if present */}
      {warnings.length > 0 && (
        <div
          style={{
            padding: "12px",
            backgroundColor: "var(--status-warning-bg)",
            border: "1px solid var(--status-warning-border)",
            borderRadius: "var(--radius-md)",
            color: "var(--status-warning-text)",
            fontSize: "13px",
            display: "flex",
            alignItems: "flex-start",
            gap: "10px",
          }}
        >
          <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: "1px" }} />
          <div>
            <div style={{ fontWeight: 600 }}>Cảnh báo ({warnings.length}):</div>
            <ul style={{ paddingLeft: "18px", marginTop: "4px" }}>
              {warnings.map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Actions */}
      <div
        style={{
          display: "flex",
          gap: "12px",
          flexWrap: "wrap",
          paddingTop: "8px",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        {outputPath && (
          <>
            <button type="button" className="btn btn-primary" onClick={handleOpenFile}>
              <ExternalLink size={16} />
              <span>Mở file</span>
            </button>
            <button type="button" className="btn btn-secondary" onClick={handleOpenFolder}>
              <Folder size={16} />
              <span>Mở thư mục</span>
            </button>
          </>
        )}
        <button type="button" className="btn btn-secondary" onClick={onReset}>
          <RefreshCw size={16} />
          <span>Xử lý file khác</span>
        </button>
      </div>
    </div>
  );
};
