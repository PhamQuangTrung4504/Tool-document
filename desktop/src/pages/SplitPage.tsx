import React, { useState } from "react";
import { FileDropzone } from "../components/FileDropzone";
import { FileCard } from "../components/FileCard";
import { ProgressModal } from "../components/ProgressModal";
import { ResultCard } from "../components/ResultCard";
import { JobStatus, IPCResponse } from "../types/ipc";
import { tauriIpc } from "../services/tauriIpc";
import { historyService } from "../services/historyService";
import { getFileName, mapErrorCodeToVietnamese } from "../utils/fileUtils";
import { Play, AlertCircle } from "lucide-react";

export const SplitPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [pagesPerSplit, setPagesPerSplit] = useState<number>(1);
  const [jobStatus, setJobStatus] = useState<JobStatus>("IDLE");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [result, setResult] = useState<IPCResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleStartSplit = async () => {
    if (!selectedFile) return;

    const baseName = selectedFile.replace(/\.pdf$/i, "");
    const outputDir = `${baseName}_split`;

    const jobId = "split_" + Date.now();
    setCurrentJobId(jobId);
    setJobStatus("RUNNING");
    setErrorMessage(null);
    setResult(null);

    const startedAt = new Date().toISOString();

    const request = {
      operation: "split" as const,
      input: selectedFile,
      output: outputDir,
      options: {
        pages_per_split: pagesPerSplit,
      },
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
          outputPath: outputDir,
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
          Chia nhỏ file PDF nhiều trang thành từng trang riêng lẻ hoặc từng phần tùy chọn.
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
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <h3 style={{ fontSize: "15px", fontWeight: 600 }}>Tùy chọn tách trang</h3>

              <div className="option-section">
                <label className="option-label">Quy tắc tách</label>
                <div className="radio-group">
                  <button
                    type="button"
                    className={`radio-btn ${pagesPerSplit === 1 ? "active" : ""}`}
                    onClick={() => setPagesPerSplit(1)}
                  >
                    Mỗi trang 1 file riêng lẻ
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
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "8px" }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ padding: "10px 24px" }}
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
