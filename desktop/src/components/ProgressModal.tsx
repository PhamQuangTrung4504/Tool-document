import React, { useEffect, useState } from "react";
import { Loader2, XCircle, AlertTriangle } from "lucide-react";
import { JobStatus } from "../types/ipc";
import { formatDuration } from "../utils/fileUtils";

interface ProgressModalProps {
  status: JobStatus;
  fileName: string;
  operation: string;
  pageCount?: number;
  warnings?: string[];
  onCancel: () => void;
}

export const ProgressModal: React.FC<ProgressModalProps> = ({
  status,
  fileName,
  operation,
  pageCount,
  warnings,
  onCancel,
}) => {
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    if (status !== "RUNNING" && status !== "QUEUED") return;

    const start = Date.now();
    const interval = setInterval(() => {
      setElapsedMs(Date.now() - start);
    }, 100);

    return () => clearInterval(interval);
  }, [status]);

  if (status === "IDLE" || status === "COMPLETED") return null;

  const getStatusText = (): string => {
    switch (status) {
      case "QUEUED":
        return "Đang chờ hàng đợi...";
      case "RUNNING":
        return "Đang xử lý tài liệu...";
      case "CANCELLED":
        return "Đã hủy xử lý";
      case "FAILED":
        return "Xử lý thất bại";
      default:
        return "Đang xử lý...";
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {status === "RUNNING" || status === "QUEUED" ? (
            <Loader2
              size={24}
              className="spin"
              style={{
                color: "var(--accent-primary)",
                animation: "spin 1s linear infinite",
              }}
            />
          ) : (
            <XCircle size={24} style={{ color: "var(--status-error-text)" }} />
          )}
          <div>
            <h3 style={{ fontSize: "16px", fontWeight: 600 }}>{getStatusText()}</h3>
            <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              {fileName}
            </p>
          </div>
        </div>

        {/* Indeterminate Progress Bar (only while running/queued) */}
        {(status === "RUNNING" || status === "QUEUED") && (
          <div className="progress-bar-container">
            <div className="progress-bar-indeterminate" />
          </div>
        )}

        {/* Metadata Details */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "8px",
            backgroundColor: "var(--bg-primary)",
            padding: "12px",
            borderRadius: "var(--radius-md)",
            fontSize: "12.5px",
          }}
        >
          <div>
            <span style={{ color: "var(--text-muted)" }}>Thao tác: </span>
            <span style={{ fontWeight: 600, textTransform: "uppercase" }}>
              {operation}
            </span>
          </div>
          <div>
            <span style={{ color: "var(--text-muted)" }}>Thời gian: </span>
            <span style={{ fontWeight: 600 }}>{formatDuration(elapsedMs)}</span>
          </div>
          {pageCount !== undefined && pageCount > 0 && (
            <div>
              <span style={{ color: "var(--text-muted)" }}>Số trang: </span>
              <span style={{ fontWeight: 600 }}>{pageCount} trang</span>
            </div>
          )}
          <div>
            <span style={{ color: "var(--text-muted)" }}>Trạng thái: </span>
            <span
              style={{
                fontWeight: 600,
                color:
                  status === "RUNNING"
                    ? "var(--accent-primary)"
                    : status === "CANCELLED"
                    ? "var(--status-warning-text)"
                    : "var(--text-primary)",
              }}
            >
              {status}
            </span>
          </div>
        </div>

        {/* Warnings if any */}
        {warnings && warnings.length > 0 && (
          <div
            style={{
              padding: "10px",
              backgroundColor: "var(--status-warning-bg)",
              border: "1px solid var(--status-warning-border)",
              borderRadius: "var(--radius-md)",
              color: "var(--status-warning-text)",
              fontSize: "12px",
              display: "flex",
              alignItems: "flex-start",
              gap: "8px",
            }}
          >
            <AlertTriangle size={16} style={{ flexShrink: 0, marginTop: "2px" }} />
            <div>
              <div style={{ fontWeight: 600 }}>Cảnh báo:</div>
              {warnings.map((w, i) => (
                <div key={i}>{w}</div>
              ))}
            </div>
          </div>
        )}

        {/* Footer actions */}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
          {(status === "RUNNING" || status === "QUEUED") && (
            <button type="button" className="btn btn-secondary" onClick={onCancel}>
              Hủy thao tác
            </button>
          )}
          {(status === "CANCELLED" || status === "FAILED") && (
            <button type="button" className="btn btn-primary" onClick={onCancel}>
              Đóng
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
