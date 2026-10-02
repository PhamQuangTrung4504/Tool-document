export function getFileName(filePath: string): string {
  if (!filePath) return "";
  const normalized = filePath.replace(/\\/g, "/");
  const parts = normalized.split("/");
  return parts[parts.length - 1] || filePath;
}

export function getFileExtension(filePath: string): string {
  const name = getFileName(filePath);
  const dotIndex = name.lastIndexOf(".");
  if (dotIndex === -1) return "";
  return name.substring(dotIndex + 1).toLowerCase();
}

export function formatBytes(bytes?: number): string {
  if (bytes === undefined || bytes === null || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export function formatDuration(ms?: number): string {
  if (!ms || ms <= 0) return "0s";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export const SUPPORTED_EXTENSIONS = [
  "pdf",
  "docx",
  "jpg",
  "jpeg",
  "png",
  "bmp",
  "tiff",
  "txt",
];

export function isSupportedExtension(ext: string): boolean {
  return SUPPORTED_EXTENSIONS.includes(ext.toLowerCase());
}

/**
 * Maps technical IPC / backend error codes to user-friendly Vietnamese messages.
 */
export function mapErrorCodeToVietnamese(code?: string, rawMessage?: string): string {
  if (!code) {
    return rawMessage || "Đã xảy ra lỗi không xác định.";
  }

  const codeMap: Record<string, string> = {
    OCR_PROCESSING_ERROR: "Không thể nhận diện nội dung trong tài liệu qua OCR.",
    UNSUPPORTED_FORMAT: "Định dạng tài liệu này chưa được hỗ trợ.",
    UNSUPPORTED_FORMAT_ERROR: "Định dạng tài liệu này chưa được hỗ trợ.",
    INVALID_DOCUMENT: "Tài liệu không hợp lệ hoặc bị hỏng.",
    INVALID_DOCUMENT_ERROR: "Tài liệu không hợp lệ hoặc bị hỏng.",
    CONVERSION_ERROR: "Không thể chuyển đổi tài liệu.",
    OPERATION_CANCELLED: "Đã hủy thao tác xử lý.",
    FILE_NOT_FOUND: "Không tìm thấy file tài liệu yêu cầu.",
    INVALID_JSON: "Yêu cầu cấu trúc dữ liệu không hợp lệ.",
    UNSUPPORTED_OPERATION: "Thao tác yêu cầu chưa được hỗ trợ.",
    BACKEND_UNAVAILABLE: "Không thể kết nối đến môi trường Python backend.",
    INTERNAL_PROCESSING_ERROR: "Đã xảy ra lỗi nội bộ trong quá trình xử lý tài liệu.",
  };

  return codeMap[code] || rawMessage || `Lỗi xử lý [${code}].`;
}
