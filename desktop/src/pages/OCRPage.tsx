import React, { useState } from "react";
import { FileDropzone } from "../components/FileDropzone";
import { FileCard } from "../components/FileCard";
import { OperationPanel } from "../components/OperationPanel";
import { ProgressModal } from "../components/ProgressModal";
import { ResultCard } from "../components/ResultCard";
import { OCRMode, JobStatus, IPCResponse } from "../types/ipc";
import { tauriIpc } from "../services/tauriIpc";
import { historyService } from "../services/historyService";
import { getFileName, mapErrorCodeToVietnamese } from "../utils/fileUtils";
import { AlertCircle } from "lucide-react";

export const OCRPage: React.FC = () => {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [ocrMode, setOcrMode] = useState<OCRMode>("auto");
  const [jobStatus, setJobStatus] = useState<JobStatus>("IDLE");
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [result, setResult] = useState<IPCResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleStart = async () => {
    if (!selectedFile) return;

    const jobId = "ocr_" + Date.now();
    setCurrentJobId(jobId);
    setJobStatus("RUNNING");
    setErrorMessage(null);
    setResult(null);

    const startedAt = new Date().toISOString();

    const request = {
      operation: "ocr" as const,
      input: selectedFile,
      options: {
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
          operation: "ocr",
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
        <h1 className="page-title">Nhận diện OCR Tiếng Việt</h1>
        <p className="page-subtitle">
          Trích xuất văn bản từ tài liệu scan và ảnh chất lượng cao với công nghệ PaddleOCR ngoại tuyến.
        </p>
      </header>

      {!selectedFile ? (
        <FileDropzone
          onFilesSelected={(files) => setSelectedFile(files[0])}
          allowedExtensions={["pdf", "png", "jpg", "jpeg", "bmp", "tiff"]}
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
            <OperationPanel
              selectedFile={selectedFile}
              operation="ocr"
              ocrMode={ocrMode}
              outputFormat="docx"
              onChangeOperation={() => {}}
              onChangeOcrMode={setOcrMode}
              onChangeOutputFormat={() => {}}
              onStart={handleStart}
              isProcessing={jobStatus === "RUNNING"}
            />
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
                <div style={{ fontWeight: 600 }}>Lỗi OCR</div>
                <div style={{ fontSize: "13px", marginTop: "2px" }}>{errorMessage}</div>
              </div>
            </div>
          )}
        </div>
      )}

      <ProgressModal
        status={jobStatus}
        fileName={selectedFile ? getFileName(selectedFile) : ""}
        operation="ocr"
        onCancel={handleCancel}
      />
    </div>
  );
};
