import React, { useState, useEffect } from "react";
import { FileDropzone } from "../components/FileDropzone";
import { FileCard } from "../components/FileCard";
import { ProgressModal } from "../components/ProgressModal";
import { ResultCard } from "../components/ResultCard";
import { JobStatus, IPCResponse } from "../types/ipc";
import { tauriIpc } from "../services/tauriIpc";
import { historyService } from "../services/historyService";
import { getFileName, mapErrorCodeToVietnamese } from "../utils/fileUtils";
import { Play, AlertCircle, Folder } from "lucide-react";

export const SplitPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [splitMode, setSplitMode] = useState<"chunk" | "range">("chunk");
  const [pagesPerSplit, setPagesPerSplit] = useState<number>(1);
  const [customChunkInput, setCustomChunkInput] = useState<string>("3");
  const [pageRangesInput, setPageRangesInput] = useState<string>("");
  const [customOutputDir, setCustomOutputDir] = useState<string | null>(null);
  const [totalPages, setTotalPages] = useState<number | null>(null);

  const [jobStatus, setJobStatus] = useState<JobStatus>("IDLE");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [result, setResult] = useState<IPCResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Fetch page count when a file is selected
  useEffect(() => {
    if (!selectedFile) {
      setTotalPages(null);
      return;
    }

    let mounted = true;
    const fetchDocInfo = async () => {
      try {
        const res = await tauriIpc.executeIpc({
          operation: "info",
          input: selectedFile,
        });
        if (mounted && res.success && res.output && typeof res.output === "object") {
          const out = res.output as Record<string, unknown>;
          const pages = (out.page_count ?? out.total_pages) as number | undefined;
          if (pages) setTotalPages(pages);
        }
      } catch (err) {
        console.warn("Failed to fetch info for split:", err);
      }
    };

    fetchDocInfo();
    return () => {
      mounted = false;
    };
  }, [selectedFile]);

  const handlePickOutputDir = async () => {
    try {
      const folder = await tauriIpc.pickFolder();
      if (folder) {
        setCustomOutputDir(folder);
      }
    } catch (err) {
      console.error("Error picking output directory:", err);
    }
  };

  const handleStartSplit = async () => {
    if (!selectedFile) return;

    const baseName = selectedFile.replace(/\.pdf$/i, "");
    const effectiveOutputDir = customOutputDir || `${baseName}_split`;

    const jobId = "split_" + Date.now();
    setCurrentJobId(jobId);
    setJobStatus("RUNNING");
    setErrorMessage(null);
    setResult(null);

    const startedAt = new Date().toISOString();

    let options: Record<string, unknown> = {};
    if (splitMode === "range") {
      if (!pageRangesInput.trim()) {
        setErrorMessage("Vui lòng nhập khoảng trang cần tách (ví dụ: 1-3, 5).");
        setJobStatus("FAILED");
        return;
      }
      options.page_ranges = pageRangesInput.trim();
    } else {
      const chunkVal = pagesPerSplit === -1 ? parseInt(customChunkInput, 10) || 1 : pagesPerSplit;
      options.pages_per_split = Math.max(1, chunkVal);
    }

    const request = {
      operation: "split" as const,
      input: selectedFile,
      output: effectiveOutputDir,
      options,
    };

    try {
      const resp = await tauriIpc.executeIpc(request, jobId);
      const completedAt = new Date().toISOString();

      if (resp.success) {
        setResult(resp);
        setJobStatus("COMPLETED");

        historyService.addEntry({
          inputName: getFileName(selectedFile),
          inputPath: selectedFile,
          outputPath: effectiveOutputDir,
          operation: "split",
          status: "COMPLETED",
          startedAt,
          completedAt,
          processingTimeMs: resp.metrics?.processing_time_ms,
        });
      } else {
        const viMsg = mapErrorCodeToVietnamese(resp.error?.code, resp.error?.message);
        setErrorMessage(viMsg);
        setJobStatus("FAILED");
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      setErrorMessage(errMsg);
      setJobStatus("FAILED");
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setResult(null);
    setErrorMessage(null);
    setJobStatus("IDLE");
    setCustomOutputDir(null);
    setTotalPages(null);
    setPageRangesInput("");
  };

  const handleCancel = async () => {
    if (currentJobId && jobStatus === "RUNNING") {
      await tauriIpc.cancelOperation(currentJobId);
      setJobStatus("CANCELLED");
    } else {
      setJobStatus("IDLE");
    }
  };

  return (
    <div className="page-container">
      <header className="page-header">
        <h1 className="page-title">Tách tài liệu PDF</h1>
        <p className="page-subtitle">
          Chia nhỏ file PDF thành từng trang riêng lẻ, theo cụm số trang hoặc theo khoảng trang tùy chỉnh.
        </p>
      </header>

      {!selectedFile ? (
        <FileDropzone
          onFilesSelected={(files) => setSelectedFile(files[0])}
          allowedExtensions={["pdf"]}
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <FileCard filePath={selectedFile} onRemove={handleReset} />

          {result ? (
            <ResultCard
              inputPath={selectedFile}
              response={result}
              onReset={handleReset}
            />
          ) : (
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ fontSize: "15px", fontWeight: 600 }}>Tùy chọn tách trang PDF</h3>
                {totalPages && (
                  <span
                    style={{
                      fontSize: "12.5px",
                      backgroundColor: "var(--accent-light)",
                      color: "var(--accent-text)",
                      padding: "4px 10px",
                      borderRadius: "var(--radius-sm)",
                      fontWeight: 600,
                    }}
                  >
                    Tài liệu gốc: {totalPages} trang
                  </span>
                )}
              </div>

              {/* Mode Selection */}
              <div className="option-section">
                <label className="option-label">Phương thức tách</label>
                <div className="radio-group">
                  <button
                    type="button"
                    className={`radio-btn ${splitMode === "chunk" ? "active" : ""}`}
                    onClick={() => setSplitMode("chunk")}
                  >
                    Theo số trang mỗi file
                  </button>
                  <button
                    type="button"
                    className={`radio-btn ${splitMode === "range" ? "active" : ""}`}
                    onClick={() => setSplitMode("range")}
                  >
                    Theo khoảng trang cụ thể
                  </button>
                </div>
              </div>

              {/* Option A: Chunk size */}
              {splitMode === "chunk" && (
                <div className="option-section">
                  <label className="option-label">Quy tắc tách theo trang</label>
                  <div className="radio-group" style={{ alignItems: "center" }}>
                    <button
                      type="button"
                      className={`radio-btn ${pagesPerSplit === 1 ? "active" : ""}`}
                      onClick={() => setPagesPerSplit(1)}
                    >
                      Mỗi trang 1 file
                    </button>
                    <button
                      type="button"
                      className={`radio-btn ${pagesPerSplit === 2 ? "active" : ""}`}
                      onClick={() => setPagesPerSplit(2)}
                    >
                      Mỗi 2 trang 1 file
                    </button>
                    <button
                      type="button"
                      className={`radio-btn ${pagesPerSplit === 5 ? "active" : ""}`}
                      onClick={() => setPagesPerSplit(5)}
                    >
                      Mỗi 5 trang 1 file
                    </button>
                    <button
                      type="button"
                      className={`radio-btn ${pagesPerSplit === -1 ? "active" : ""}`}
                      onClick={() => setPagesPerSplit(-1)}
                    >
                      Tự nhập số trang...
                    </button>
                  </div>

                  {pagesPerSplit === -1 && (
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "10px" }}>
                      <span style={{ fontSize: "13px", color: "var(--text-secondary)" }}>
                        Số trang trong mỗi file mới:
                      </span>
                      <input
                        type="number"
                        min="1"
                        max={totalPages || 999}
                        value={customChunkInput}
                        onChange={(e) => setCustomChunkInput(e.target.value)}
                        style={{
                          width: "80px",
                          padding: "6px 10px",
                          borderRadius: "var(--radius-md)",
                          border: "1px solid var(--border-subtle)",
                          backgroundColor: "var(--bg-primary)",
                          color: "var(--text-primary)",
                          fontSize: "13.5px",
                          fontWeight: 600,
                        }}
                      />
                      <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>trang / file</span>
                    </div>
                  )}
                </div>
              )}

              {/* Option B: Specific Page Ranges */}
              {splitMode === "range" && (
                <div className="option-section">
                  <label className="option-label">Nhập khoảng trang cụ thể</label>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <input
                      type="text"
                      placeholder="Ví dụ: 1-3, 5, 7-10 (hoặc 1, 2, 4)"
                      value={pageRangesInput}
                      onChange={(e) => setPageRangesInput(e.target.value)}
                      style={{
                        padding: "8px 12px",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--border-subtle)",
                        backgroundColor: "var(--bg-primary)",
                        color: "var(--text-primary)",
                        fontSize: "13.5px",
                        width: "100%",
                      }}
                    />
                    <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      Cú pháp: Dùng dấu gạch nối <code>-</code> cho khoảng trang (ví dụ <code>1-3</code>) và dấu phẩy <code>,</code> giữa các phần cần tách.
                    </span>
                  </div>
                </div>
              )}

              {/* Output Directory Selection */}
              <div className="option-section">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <label className="option-label">Thư mục lưu các file đã tách</label>
                  {customOutputDir && (
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
                      onClick={() => setCustomOutputDir(null)}
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
                      color: customOutputDir ? "var(--text-primary)" : "var(--text-muted)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={customOutputDir || (selectedFile ? `${selectedFile.replace(/\.pdf$/i, "")}_split` : "")}
                  >
                    📁 {customOutputDir || (selectedFile ? `Mặc định: ${selectedFile.replace(/\.pdf$/i, "")}_split` : "Thư mục riêng theo file")}
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: "8px 14px", fontSize: "12.5px", whiteSpace: "nowrap" }}
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
                  disabled={jobStatus === "RUNNING"}
                  onClick={handleStartSplit}
                >
                  <Play size={16} fill="currentColor" />
                  <span>Bắt đầu tách PDF</span>
                </button>
              </div>
            </div>
          )}

          {errorMessage && (
            <div
              style={{
                padding: "14px",
                backgroundColor: "var(--status-error-bg)",
                border: "1px solid var(--status-error-border)",
                borderRadius: "var(--radius-md)",
                color: "var(--status-error-text)",
                display: "flex",
                alignItems: "flex-start",
                gap: "10px",
              }}
            >
              <AlertCircle size={20} style={{ flexShrink: 0, marginTop: "1px" }} />
              <div>
                <div style={{ fontWeight: 600 }}>Không thể tách PDF</div>
                <div style={{ fontSize: "13px", marginTop: "2px" }}>{errorMessage}</div>
              </div>
            </div>
          )}
        </div>
      )}

      <ProgressModal
        status={jobStatus}
        fileName={selectedFile ? getFileName(selectedFile) : ""}
        operation="split"
        onCancel={handleCancel}
      />
    </div>
  );
};
