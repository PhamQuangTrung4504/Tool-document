import { OperationType } from "./ipc";

export interface HistoryItem {
  id: string;
  inputName: string;
  inputPath: string;
  outputPath?: string;
  operation: OperationType;
  status: "COMPLETED" | "FAILED" | "CANCELLED";
  startedAt: string;
  completedAt: string;
  processingTimeMs?: number;
  pages?: number;
  warnings?: string[];
  errorMessage?: string;
}
