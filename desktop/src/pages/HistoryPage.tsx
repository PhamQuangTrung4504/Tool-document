import React, { useState, useEffect } from "react";
import { historyService } from "../services/historyService";
import { HistoryItem } from "../types/history";
import { tauriIpc } from "../services/tauriIpc";
import { formatDuration } from "../utils/fileUtils";
import {
  Trash2,
  ExternalLink,
  Folder,
  History as HistoryIcon,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from "lucide-react";

export const HistoryPage: React.FC = () => {
  const [historyList, setHistoryList] = useState<HistoryItem[]>([]);

  const loadHistory = () => {
    setHistoryList(historyService.getHistory());
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleRemoveItem = (id: string) => {
    historyService.removeEntry(id);
    loadHistory();
  };

  const handleClearHistory = () => {
    if (confirm("Bạn có chắc chắn muốn xóa toàn bộ lịch sử thao tác?")) {
      historyService.clearHistory();
      loadHistory();
    }
  };

  const handleOpenFile = async (path?: string) => {
    if (path) {
      await tauriIpc.openFile(path);
    }
  };

  const handleOpenFolder = async (path?: string) => {
    if (path) {
      await tauriIpc.openFolder(path);
    }
  };

  return (
    <div className="page-container">
      <header
        className="page-header"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexDirection: "row",
        }}
      >
        <div>
          <h1 className="page-title">Lịch sử xử lý</h1>
          <p className="page-subtitle">
            Danh sách tối đa 100 tác vụ đã xử lý gần đây (lưu trữ cục bộ).
          </p>
        </div>

        {historyList.length > 0 && (
          <button
            type="button"
            className="btn btn-secondary"
            style={{ color: "var(--status-error-text)" }}
            onClick={handleClearHistory}
          >
            <Trash2 size={16} />
            <span>Xóa toàn bộ lịch sử</span>
          </button>
        )}
      </header>

      {historyList.length === 0 ? (
        <div
          className="card"
          style={{
            padding: "48px 24px",
            textAlign: "center",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "12px",
          }}
        >
          <HistoryIcon size={40} style={{ color: "var(--text-muted)", opacity: 0.6 }} />
          <div style={{ fontSize: "16px", fontWeight: 600 }}>Chưa có lịch sử thao tác</div>
          <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            Các tác vụ chuyển đổi và OCR thành công hoặc thất bại sẽ được ghi nhận tại đây.
          </p>
        </div>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Tài liệu</th>
                <th>Thao tác</th>
                <th>Trạng thái</th>
                <th>Thời gian</th>
                <th>Thời điểm</th>
                <th style={{ textAlign: "right" }}>Tác vụ</th>
              </tr>
            </thead>
            <tbody>
              {historyList.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{item.inputName}</div>
                    <div
                      style={{
                        fontSize: "12px",
                        color: "var(--text-muted)",
                        maxWidth: "260px",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={item.inputPath}
                    >
                      {item.inputPath}
                    </div>
                  </td>
                  <td>
                    <span
                      style={{
                        textTransform: "uppercase",
                        fontWeight: 600,
                        fontSize: "12px",
                        backgroundColor: "var(--bg-primary)",
                        padding: "3px 6px",
                        borderRadius: "var(--radius-sm)",
                      }}
                    >
                      {item.operation}
                    </span>
                  </td>
                  <td>
                    <span
                      className={`status-chip ${
                        item.status === "COMPLETED"
                          ? "success"
                          : item.status === "FAILED"
                          ? "error"
                          : "warning"
                      }`}
                    >
                      {item.status === "COMPLETED" ? (
                        <CheckCircle2 size={13} />
                      ) : item.status === "FAILED" ? (
                        <XCircle size={13} />
                      ) : (
                        <AlertTriangle size={13} />
                      )}
                      <span>
                        {item.status === "COMPLETED"
                          ? "Hoàn tất"
                          : item.status === "FAILED"
                          ? "Thất bại"
                          : "Đã hủy"}
                      </span>
                    </span>
                  </td>
                  <td style={{ color: "var(--text-muted)", fontSize: "13px" }}>
                    {formatDuration(item.processingTimeMs)}
                  </td>
                  <td style={{ color: "var(--text-muted)", fontSize: "12.5px" }}>
                    {new Date(item.startedAt).toLocaleTimeString("vi-VN", {
                      hour: "2-digit",
                      minute: "2-digit",
                      day: "2-digit",
                      month: "2-digit",
                    })}
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "flex-end",
                        gap: "6px",
                      }}
                    >
                      {item.outputPath && (
                        <>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: "4px 8px" }}
                            title="Mở file kết quả"
                            onClick={() => handleOpenFile(item.outputPath)}
                          >
                            <ExternalLink size={14} />
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: "4px 8px" }}
                            title="Mở thư mục chứa file"
                            onClick={() => handleOpenFolder(item.outputPath)}
                          >
                            <Folder size={14} />
                          </button>
                        </>
                      )}
                      <button
                        type="button"
                        className="btn"
                        style={{
                          padding: "4px 8px",
                          color: "var(--text-muted)",
                          background: "transparent",
                        }}
                        title="Xóa mục này"
                        onClick={() => handleRemoveItem(item.id)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
