import React, { useState, useEffect } from "react";
import { BackendStatus, OCRMode } from "../types/ipc";
import { tauriIpc } from "../services/tauriIpc";
import { CheckCircle2, XCircle, Folder, RefreshCw } from "lucide-react";

interface SettingsPageProps {
  currentTheme: "light" | "dark" | "system";
  onChangeTheme: (theme: "light" | "dark" | "system") => void;
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  currentTheme,
  onChangeTheme,
}) => {
  const [defaultOcrMode, setDefaultOcrMode] = useState<OCRMode>("auto");
  const [outputDirMode, setOutputDirMode] = useState<"default" | "custom">("default");
  const [customOutputDir, setCustomOutputDir] = useState<string>("");
  const [keepTempFiles, setKeepTempFiles] = useState<boolean>(false);
  const [status, setStatus] = useState<BackendStatus | null>(null);
  const [isLoadingStatus, setIsLoadingStatus] = useState<boolean>(false);

  const fetchStatus = async () => {
    setIsLoadingStatus(true);
    try {
      const st = await tauriIpc.getBackendStatus();
      setStatus(st);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoadingStatus(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handlePickCustomDir = async () => {
    try {
      const folder = await tauriIpc.pickFolder();
      if (folder) {
        setCustomOutputDir(folder);
        setOutputDirMode("custom");
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="page-container">
      <header className="page-header">
        <h1 className="page-title">Cài đặt ứng dụng</h1>
        <p className="page-subtitle">
          Tùy chỉnh cấu hình xử lý và kiểm tra trạng thái hoạt động của hệ thống.
        </p>
      </header>

      <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
        {/* Backend Status Card */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ fontSize: "15px", fontWeight: 600 }}>Trạng thái Backend</h3>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: "4px 10px", fontSize: "12px" }}
              disabled={isLoadingStatus}
              onClick={fetchStatus}
            >
              <RefreshCw size={13} className={isLoadingStatus ? "spin" : ""} />
              <span>Kiểm tra lại</span>
            </button>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "12px",
            }}
          >
            <div
              style={{
                padding: "12px",
                backgroundColor: "var(--bg-primary)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Backend Engine</div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px" }}>
                {status?.ready ? (
                  <CheckCircle2 size={16} style={{ color: "var(--status-success-text)" }} />
                ) : (
                  <XCircle size={16} style={{ color: "var(--status-error-text)" }} />
                )}
                <span style={{ fontWeight: 600 }}>{status?.ready ? "Sẵn sàng (Ready)" : "Chưa kết nối"}</span>
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                backgroundColor: "var(--bg-primary)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Python Environment</div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px" }}>
                {status?.python_detected ? (
                  <CheckCircle2 size={16} style={{ color: "var(--status-success-text)" }} />
                ) : (
                  <XCircle size={16} style={{ color: "var(--status-error-text)" }} />
                )}
                <span style={{ fontWeight: 600 }}>
                  {status?.python_version || (status?.python_detected ? "Đã phát hiện" : "Không tìm thấy")}
                </span>
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                backgroundColor: "var(--bg-primary)",
                borderRadius: "var(--radius-md)",
              }}
            >
              <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>PaddleOCR Offline</div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px" }}>
                {status?.ocr_available ? (
                  <CheckCircle2 size={16} style={{ color: "var(--status-success-text)" }} />
                ) : (
                  <XCircle size={16} style={{ color: "var(--status-warning-text)" }} />
                )}
                <span style={{ fontWeight: 600 }}>
                  {status?.ocr_available ? "Khả dụng (Available)" : "Chưa cài Paddle"}
                </span>
              </div>
            </div>
          </div>

          {status && (
            <div
              style={{
                fontSize: "12px",
                color: "var(--text-muted)",
                backgroundColor: "var(--bg-primary)",
                padding: "10px 12px",
                borderRadius: "var(--radius-md)",
              }}
            >
              <div>Python: <code>{status.python_path || "N/A"}</code></div>
              <div style={{ marginTop: "4px" }}>Backend: <code>{status.backend_path || "N/A"}</code></div>
            </div>
          )}
        </div>

        {/* 1. Default OCR Mode */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <h3 style={{ fontSize: "15px", fontWeight: 600 }}>1. Chế độ OCR mặc định</h3>
          <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            Chọn chế độ ưu tiên cho các tác vụ nhận diện văn bản OCR.
          </p>
          <div className="radio-group">
            <button
              type="button"
              className={`radio-btn ${defaultOcrMode === "auto" ? "active" : ""}`}
              onClick={() => setDefaultOcrMode("auto")}
            >
              Auto (Tự động)
            </button>
            <button
              type="button"
              className={`radio-btn ${defaultOcrMode === "fast" ? "active" : ""}`}
              onClick={() => setDefaultOcrMode("fast")}
            >
              Fast (Nhanh ~4.5s)
            </button>
            <button
              type="button"
              className={`radio-btn ${defaultOcrMode === "full" ? "active" : ""}`}
              onClick={() => setDefaultOcrMode("full")}
            >
              Full (Đầy đủ & Bảng ~5.7s)
            </button>
          </div>
        </div>

        {/* 2. Output Directory */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <h3 style={{ fontSize: "15px", fontWeight: 600 }}>2. Thư mục lưu kết quả</h3>
          <div className="radio-group">
            <button
              type="button"
              className={`radio-btn ${outputDirMode === "default" ? "active" : ""}`}
              onClick={() => setOutputDirMode("default")}
            >
              Mặc định (Cùng thư mục với file gốc)
            </button>
            <button
              type="button"
              className={`radio-btn ${outputDirMode === "custom" ? "active" : ""}`}
              onClick={handlePickCustomDir}
            >
              Tùy chỉnh...
            </button>
          </div>
          {outputDirMode === "custom" && customOutputDir && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "13px",
                color: "var(--text-primary)",
                backgroundColor: "var(--bg-primary)",
                padding: "8px 12px",
                borderRadius: "var(--radius-md)",
              }}
            >
              <Folder size={16} />
              <span>{customOutputDir}</span>
            </div>
          )}
        </div>

        {/* 3. Keep Temporary Files */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h3 style={{ fontSize: "15px", fontWeight: 600 }}>3. Giữ lại file tạm thời (Debug)</h3>
              <p style={{ fontSize: "13px", color: "var(--text-muted)", marginTop: "2px" }}>
                Mặc định tắt. Bật tùy chọn này để kiểm tra các file ảnh trung gian được cắt ra.
              </p>
            </div>
            <label style={{ display: "flex", alignItems: "center", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={keepTempFiles}
                onChange={(e) => setKeepTempFiles(e.target.checked)}
                style={{ width: "18px", height: "18px", cursor: "pointer" }}
              />
            </label>
          </div>
        </div>

        {/* 4. Theme */}
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <h3 style={{ fontSize: "15px", fontWeight: 600 }}>4. Giao diện (Theme)</h3>
          <div className="radio-group">
            <button
              type="button"
              className={`radio-btn ${currentTheme === "light" ? "active" : ""}`}
              onClick={() => onChangeTheme("light")}
            >
              Sáng (Light)
            </button>
            <button
              type="button"
              className={`radio-btn ${currentTheme === "dark" ? "active" : ""}`}
              onClick={() => onChangeTheme("dark")}
            >
              Tối (Dark)
            </button>
            <button
              type="button"
              className={`radio-btn ${currentTheme === "system" ? "active" : ""}`}
              onClick={() => onChangeTheme("system")}
            >
              Hệ thống (System)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
