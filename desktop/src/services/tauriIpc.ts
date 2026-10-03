import { invoke } from "@tauri-apps/api/core";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { BackendStatus, FolderFileItem, IPCRequest, IPCResponse } from "../types/ipc";

export const isTauriEnvironment = (): boolean => {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
};

export const tauriIpc = {
  async executeIpc(request: IPCRequest, jobId?: string): Promise<IPCResponse> {
    if (!isTauriEnvironment()) {
      console.warn("Running outside Tauri environment. Returning mock IPC response.");
      return {
        success: true,
        operation: request.operation,
        output: typeof request.input === "string" ? `${request.input}.out` : "output_merged.pdf",
        metrics: { pages: 1, processing_time_ms: 1200, ocr_mode: "auto" },
        warnings: [],
      };
    }

    try {
      const response = await invoke<IPCResponse>("execute_ipc", {
        request,
        jobId: jobId || null,
      });
      return response;
    } catch (err: unknown) {
      if (typeof err === "object" && err !== null && "error" in err) {
        return err as IPCResponse;
      }
      return {
        success: false,
        error: {
          code: "IPC_INVOKE_ERROR",
          message: typeof err === "string" ? err : "Lỗi không xác định khi gọi backend.",
        },
      };
    }
  },

  async cancelOperation(jobId: string): Promise<boolean> {
    if (!isTauriEnvironment()) {
      return true;
    }
    try {
      return await invoke<boolean>("cancel_operation", { jobId });
    } catch {
      return false;
    }
  },

  async getBackendStatus(): Promise<BackendStatus> {
    if (!isTauriEnvironment()) {
      return {
        ready: true,
        python_detected: true,
        python_path: "python.exe (browser mock)",
        python_version: "Python 3.13 (Mock)",
        backend_path: "d:/Code/Tool-document/backend",
        ocr_available: true,
      };
    }

    try {
      return await invoke<BackendStatus>("get_backend_status");
    } catch (e) {
      return {
        ready: false,
        python_detected: false,
        python_path: "",
        python_version: "",
        backend_path: "",
        ocr_available: false,
      };
    }
  },

  async openFile(path: string): Promise<void> {
    if (!isTauriEnvironment()) {
      alert(`Mở file: ${path}`);
      return;
    }
    await invoke("open_file", { path });
  },

  async openFolder(path: string): Promise<void> {
    if (!isTauriEnvironment()) {
      alert(`Mở thư mục: ${path}`);
      return;
    }
    await invoke("open_folder", { path });
  },

  async pickFiles(multiple: boolean = false, allowedExtensions?: string[]): Promise<string[]> {
    if (!isTauriEnvironment()) {
      // In browser fallback
      return [];
    }

    const filters = allowedExtensions
      ? [{ name: "Tài liệu được hỗ trợ", extensions: allowedExtensions }]
      : [
          {
            name: "Tài liệu & Hình ảnh",
            extensions: ["pdf", "docx", "png", "jpg", "jpeg", "bmp", "tiff", "txt"],
          },
        ];

    const selected = await openDialog({
      multiple,
      directory: false,
      filters,
    });

    if (!selected) return [];
    if (Array.isArray(selected)) {
      return selected;
    }
    return [selected];
  },

  async pickFolder(): Promise<string | null> {
    if (!isTauriEnvironment()) return null;
    const selected = await openDialog({
      multiple: false,
      directory: true,
    });
    if (!selected || Array.isArray(selected)) return null;
    return selected;
  },

  async listFilesInFolder(folderPath: string): Promise<FolderFileItem[]> {
    if (isTauriEnvironment()) {
      try {
        const items = await invoke<FolderFileItem[]>("list_files_in_folder", {
          folderPath,
        });
        if (items && Array.isArray(items)) {
          return items;
        }
      } catch (err) {
        console.warn("Native list_files_in_folder failed, falling back to python IPC:", err);
      }
    }

    // Python IPC fallback
    try {
      const resp = await this.executeIpc({
        operation: "list_files",
        input: folderPath,
      });
      if (resp.success && Array.isArray(resp.output)) {
        return resp.output as FolderFileItem[];
      }
    } catch (e) {
      console.error("Failed to list files via IPC:", e);
    }
    return [];
  },
};
