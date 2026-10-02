import React from "react";
import { Trash2, ArrowRight, ScanText, AlertTriangle } from "lucide-react";
import { getFileName, getFileExtension, isSupportedExtension } from "../utils/fileUtils";

interface FileCardProps {
  filePath: string;
  pages?: number;
  onRemove: () => void;
  onConvert?: () => void;
  onOcr?: () => void;
  compact?: boolean;
}

export const FileCard: React.FC<FileCardProps> = ({
  filePath,
  pages,
  onRemove,
  onConvert,
  onOcr,
  compact = false,
}) => {
  const name = getFileName(filePath);
  const ext = getFileExtension(filePath);
  const isSupported = isSupportedExtension(ext);

  return (
    <div
      className="file-card"
      style={{
        borderColor: !isSupported ? "var(--status-error-border)" : undefined,
      }}
    >
      <div className="file-info">
        <div
          className="file-icon-badge"
          style={{
            backgroundColor: !isSupported ? "var(--status-error-bg)" : undefined,
            color: !isSupported ? "var(--status-error-text)" : undefined,
          }}
        >
          {ext.toUpperCase().substring(0, 4) || "FILE"}
        </div>
        <div className="file-meta">
          <div className="file-name" title={filePath}>
            {name}
          </div>
          <div className="file-details">
            <span>{ext.toUpperCase()}</span>
            {pages !== undefined && pages > 0 && <span>• {pages} trang</span>}
            {!isSupported && (
              <span
                style={{
                  color: "var(--status-error-text)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <AlertTriangle size={13} />
                Định dạng chưa được hỗ trợ
              </span>
            )}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        {!compact && isSupported && onConvert && (
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: "6px 12px", fontSize: "12.5px" }}
            onClick={onConvert}
          >
            <ArrowRight size={14} />
            <span>Chuyển đổi</span>
          </button>
        )}
        {!compact && isSupported && onOcr && (
          <button
            type="button"
            className="btn btn-secondary"
            style={{ padding: "6px 12px", fontSize: "12.5px" }}
            onClick={onOcr}
          >
            <ScanText size={14} />
            <span>OCR</span>
          </button>
        )}
        <button
          type="button"
          className="btn"
          style={{
            padding: "6px",
            color: "var(--text-muted)",
            background: "transparent",
          }}
          title="Xóa khỏi danh sách"
          onClick={onRemove}
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
};
