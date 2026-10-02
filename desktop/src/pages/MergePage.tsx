import React, { useState } from "react";
import { FileCard } from "../components/FileCard";
import { ProgressModal } from "../components/ProgressModal";
import { ResultCard } from "../components/ResultCard";
import { JobStatus, IPCResponse } from "../types/ipc";
import { tauriIpc } from "../services/tauriIpc";
import { historyService } from "../services/historyService";
import { getFileName, mapErrorCodeToVietnamese } from "../utils/fileUtils";
import { Plus, Files, Play, AlertCircle } from "lucide-react";

export const MergePage: React.FC = () => {
  const [files, setFiles] = useState<string[]>([]);
  const [jobStatus, setJobStatus] = useState<JobStatus>("IDLE");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [result, setResult] = useState<IPCResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleAddFiles = async () => {
    try {
      const selected = await tauriIpc.pickFiles(true, ["pdf"]);
      if (selected.length > 0) {
        setFiles((prev) => [...prev, ...selected]);
        setResult(null);
        setErrorMessage(null);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleStartMerge = async () => {
    if (files.length < 2) {
      setErrorMessage("Cần ít nhất 2 file PDF để tiến hành ghép nối.");
      return;
    }

    const first = files[0];
    const outputPath = first.replace(/\.pdf$/i, "_merged.pdf");

    const jobId = "merge_" + Date.now();
    setCurrentJobId(jobId);
    setJobStatus("RUNNING");
    setErrorMessage(null);
    setResult(null);

    const startedAt = new Date().toISOString();

    const request = {
      operation: "merge" as const,
      input: files,
      output: outputPath,
    };

    try {
      const resp = await tauriIpc.executeIpc(request, jobId);
      const completedAt = new Date().toISOString();

      if (resp.success) {
        setResult(resp);
        setJobStatus("COMPLETED");

        historyService.addEntry({
          inputName: `${files.length} files PDF`,
          inputPath: first,
          outputPath,
          operation: "merge",
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
    setFiles([]);
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
        <h1 className="page-title">Ghép tài liệu PDF</h1>
        <p className="page-subtitle">
          Nối nhiều tập tin PDF thành một file duy nhất theo thứ tự lựa chọn.
        </p>
      </header>

      {result ? (
        <ResultCard
          inputPath={files[0] || "Merged Files"}
          response={result}
          onReset={handleReset}
        />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div style={{ fontSize: "14px", fontWeight: 600 }}>
              Danh sách file ({files.length})
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleAddFiles}
            >
              <Plus size={16} />
              <span>Thêm file PDF</span>
            </button>
          </div>

          {files.length === 0 ? (
            <div
              className="card"
              style={{
                padding: "48px 24px",
                textAlign: "center",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "12px",
                cursor: "pointer",
              }}
              onClick={handleAddFiles}
            >
              <Files size={40} style={{ color: "var(--accent-primary)" }} />
              <div style={{ fontSize: "16px", fontWeight: 600 }}>
                Chưa chọn file PDF nào
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                Nhấn vào đây để chọn các file PDF cần ghép lại với nhau
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {files.map((filePath, index) => (
                <FileCard
                  key={index}
                  filePath={filePath}
                  compact
                  onRemove={() => handleRemoveFile(index)}
                />
              ))}

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  marginTop: "16px",
                }}
              >
                <button
                  type="button"
                  className="btn btn-primary"
                  style={{ padding: "10px 24px" }}
                  disabled={files.length < 2 || jobStatus === "RUNNING"}
                  onClick={handleStartMerge}
                >
                  <Play size={16} fill="currentColor" />
                  <span>Ghép {files.length} file PDF</span>
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
                <div style={{ fontWeight: 600 }}>Không thể ghép PDF</div>
                <div style={{ fontSize: "13px", marginTop: "2px" }}>{errorMessage}</div>
              </div>
            </div>
          )}
        </div>
      )}

      <ProgressModal
        status={jobStatus}
        fileName={files.length > 0 ? getFileName(files[0]) : ""}
        operation="merge"
        onCancel={handleCancel}
      />
    </div>
  );
};
