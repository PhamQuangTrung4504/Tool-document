export type OperationType = "convert" | "ocr" | "info" | "merge" | "split" | "list_files";

export type OCRMode = "auto" | "fast" | "full";

export type OutputFormat = "docx" | "pdf" | "txt" | "html" | "md";

export interface FolderFileItem {
  name: string;
  path: string;
  size_bytes: number;
  ext: string;
}

export type JobStatus = "IDLE" | "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface IPCOptions {
  to_format?: OutputFormat;
  ocr_mode?: OCRMode;
  force_ocr?: boolean;
  lang?: string;
  pages_per_split?: number;
  [key: string]: unknown;
}

export interface IPCRequest {
  operation: OperationType;
  input: string | string[];
  output?: string;
  options?: IPCOptions;
}

export interface Metrics {
  pages?: number;
  processing_time_ms?: number;
  ocr_mode?: string;
  input_count?: number;
  chunks?: number;
  text_coverage?: number;
}

export interface IPCError {
  code: string;
  message: string;
}

export interface IPCResponse {
  success: boolean;
  operation?: string;
  output?: string | string[] | unknown;
  metrics?: Metrics;
  warnings?: string[];
  error?: IPCError;
}

export interface BackendStatus {
  ready: boolean;
  python_detected: boolean;
  python_path: string;
  python_version: string;
  backend_path: string;
  ocr_available: boolean;
}
