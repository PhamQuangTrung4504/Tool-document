import React, { useState } from "react";
import { FileDropzone } from "../components/FileDropzone";
import { FileCard } from "../components/FileCard";
import { OperationPanel } from "../components/OperationPanel";
import { ProgressModal } from "../components/ProgressModal";
import { ResultCard } from "../components/ResultCard";
import { DocumentPreview } from "../components/DocumentPreview";
import { OperationType, OCRMode, OutputFormat, JobStatus, IPCResponse } from "../types/ipc";
import { tauriIpc } from "../services/tauriIpc";
import { historyService } from "../services/historyService";
import { getFileName, formatDuration, mapErrorCodeToVietnamese } from "../utils/fileUtils";
import { History as HistoryIcon, Clock, CheckCircle2, XCircle, AlertCircle } from "lucide-react";

export const HomePage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [operation, setOperation] = useState<OperationType>("convert");
  const [ocrMode, setOcrMode] = useState<OCRMode>("auto");
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("docx");

  const [jobStatus, setJobStatus] = useState<JobStatus>("IDLE");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [result, setResult] = useState<IPCResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const recentHistory = historyService.getHistory().slice(0, 5);

  const handleFilesSelected = (files: string[]) => {
    if (files.length > 0) {
      setSelectedFile(files[0]);
      setResult(null);
      setErrorMessage(null);
    }
  };

  const handleStart = async () => {
    if (!selectedFile) return;

    const jobId = "job_" + Date.now();
    setCurrentJobId(jobId);
    setJobStatus("RUNNING");
    setErrorMessage(null);
    setResult(null);

    const startedAt = new Date().toISOString();

    const request = {
      operation,
      input: selectedFile,
      options: {
        to_format: outputFormat,
        ocr_mode: ocrMode,
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
          outputPath: typeof resp.output === "string" ? resp.output : undefined,
          operation,
          status: "COMPLETED",
          startedAt,
          completedAt,
          processingTimeMs: resp.metrics?.processing_time_ms,
          pages: resp.metrics?.pages,
          warnings: resp.warnings,
        });
      } else {
        const viMsg = mapErrorCodeToVietnamese(resp.error?.code, resp.error?.message);
        setErrorMessage(viMsg);
        setJobStatus("FAILED");

        historyService.addEntry({
          inputName: getFileName(selectedFile),
          inputPath: selectedFile,
          operation,
          status: "FAILED",
          startedAt,
          completedAt,
          errorMessage: viMsg,
        });
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      setErrorMessage(errMsg);
      setJobStatus("FAILED");
    }
  };

  const handleCancel = async () => {
    if (currentJobId && jobStatus === "RUNNING") {
      await tauriIpc.cancelOperation(currentJobId);
      setJobStatus("CANCELLED");
    } else {
      setJobStatus("IDLE");
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setResult(null);
    setErrorMessage(null);
    setJobStatus("IDLE");
  };

  return (
    <div className="page-container">
      <header className="page-header">
        <h1 className="page-title">Document Assistant</h1>
        <p className="page-subtitle">
          Xử lý và chuyển đổi tài liệu ngay trên máy tính.
        </p>
      </header>

      {/* Main Drag-and-Drop Area if no file selected */}
      {!selectedFile ? (
        <>
          <FileDropzone onFilesSelected={handleFilesSelected} />

          {/* Recent Operations Section */}
          <div className="card" style={{ marginTop: "10px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "16px",
              }}
            >
              <HistoryIcon size={18} style={{ color: "var(--accent-primary)" }} />
              <h3 style={{ fontSize: "15px", fontWeight: 600 }}>Thao tác gần đây</h3>
            </div>

            {recentHistory.length === 0 ? (
              <div
                style={{
                  textAlign: "center",
                  padding: "24px 0",
                  color: "var(--text-muted)",
                  fontSize: "13.5px",
                }}
              >
                Chưa có thao tác nào gần đây. Hãy kéo thả file để bắt đầu!
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Tên file</th>
                    <th>Thao tác</th>
                    <th>Trạng thái</th>
                    <th>Thời gian</th>
                  </tr>
                </thead>
                <tbody>
                  {recentHistory.map((item) => (
                    <tr key={item.id}>
                      <td style={{ fontWeight: 500 }}>{item.inputName}</td>
                      <td style={{ textTransform: "uppercase", fontSize: "12px" }}>
                        {item.operation}
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
                            <CheckCircle2 size={12} />
                          ) : (
                            <XCircle size={12} />
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
                      <td style={{ color: "var(--text-muted)" }}>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                          <Clock size={12} />
                          {formatDuration(item.processingTimeMs)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <FileCard
            filePath={selectedFile}
            onRemove={handleReset}
            onConvert={() => setOperation("convert")}
            onOcr={() => setOperation("ocr")}
          />

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 340px",
              gap: "16px",
              alignItems: "start",
            }}
          >
            <div>
              {result ? (
                <ResultCard
                  inputPath={selectedFile}
                  response={result}
                  onReset={handleReset}
                />
              ) : (
                <OperationPanel
                  selectedFile={selectedFile}
                  operation={operation}
                  ocrMode={ocrMode}
                  outputFormat={outputFormat}
                  onChangeOperation={setOperation}
                  onChangeOcrMode={setOcrMode}
                  onChangeOutputFormat={setOutputFormat}
                  onStart={handleStart}
                  isProcessing={jobStatus === "RUNNING"}
                />
              )}

              {/* Error display */}
              {errorMessage && (
                <div
                  style={{
                    marginTop: "16px",
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
                    <div style={{ fontWeight: 600 }}>Không thể hoàn thành xử lý</div>
                    <div style={{ fontSize: "13px", marginTop: "2px" }}>{errorMessage}</div>
                  </div>
                </div>
              )}
            </div>

            <DocumentPreview filePath={selectedFile} />
          </div>
        </div>
      )}

      {/* Progress Modal */}
      <ProgressModal
        status={jobStatus}
        fileName={selectedFile ? getFileName(selectedFile) : ""}
        operation={operation}
        onCancel={handleCancel}
      />
    </div>
  );
};
