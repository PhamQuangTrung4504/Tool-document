import React, { useEffect, useState } from "react";
import { FileText, Image as ImageIcon, Eye, FileCheck } from "lucide-react";
import { getFileExtension, getFileName, formatBytes, getFileParentDir } from "../utils/fileUtils";
import { tauriIpc } from "../services/tauriIpc";

interface DocumentPreviewProps {
  filePath: string;
}

interface DocInfoState {
  page_count?: number;
  total_pages?: number;
  size_bytes?: number;
  title?: string;
  pdf_type?: string;
  paragraph_count?: number;
  table_count?: number;
  line_count?: number;
  width?: number;
  height?: number;
}

export const DocumentPreview: React.FC<DocumentPreviewProps> = ({ filePath }) => {
  const ext = getFileExtension(filePath);
  const name = getFileName(filePath);
  const [docInfo, setDocInfo] = useState<DocInfoState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);

    const fetchInfo = async () => {
      try {
        const res = await tauriIpc.executeIpc({
          operation: "info",
          input: filePath,
        });
        if (mounted && res.success && res.output && typeof res.output === "object") {
          const out = res.output as DocInfoState;
          setDocInfo({
            ...out,
            page_count: out.page_count ?? out.total_pages,
          });
        }
      } catch (err) {
        console.warn("Failed to fetch doc info:", err);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchInfo();
    return () => {
      mounted = false;
    };
  }, [filePath]);

  const isImage = ["jpg", "jpeg", "png", "bmp", "webp", "tiff"].includes(ext);

  const getPdfTypeLabel = (type?: string) => {
    switch (type) {
      case "text_based":
        return "Văn bản số (Text layer chuẩn)";
      case "scanned":
        return "Bản scan hình ảnh (Cần OCR)";
      case "mixed":
        return "Hỗn hợp (Văn bản & Quét)";
      default:
        return null;
    }
  };

  const getFormatBadgeColor = () => {
    if (ext === "pdf") return "#ef4444";
    if (ext === "docx") return "#2563eb";
    if (ext === "txt" || ext === "md") return "#059669";
    if (isImage) return "#f59e0b";
    return "var(--accent-primary)";
  };

  return (
    <div
      className="card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "14px",
        padding: "16px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Eye size={16} style={{ color: "var(--accent-primary)" }} />
          <h4 style={{ fontSize: "14px", fontWeight: 600 }}>Xem trước thông tin</h4>
        </div>
        {loading && (
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Đang phân tích...</span>
        )}
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          backgroundColor: "var(--bg-primary)",
          padding: "14px",
          borderRadius: "var(--radius-md)",
          fontSize: "13px",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
          {isImage ? (
            <ImageIcon size={22} style={{ color: getFormatBadgeColor(), flexShrink: 0, marginTop: "2px" }} />
          ) : (
            <FileText size={22} style={{ color: getFormatBadgeColor(), flexShrink: 0, marginTop: "2px" }} />
          )}
          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              style={{
                fontWeight: 600,
                color: "var(--text-primary)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              title={name}
            >
              {name}
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
              {getFileParentDir(filePath) || "Thư mục hiện tại"}
            </div>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "8px",
            marginTop: "6px",
            paddingTop: "10px",
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          <div>
            <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>Định dạng: </span>
            <strong style={{ color: getFormatBadgeColor() }}>{ext.toUpperCase()}</strong>
          </div>

          <div>
            <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>Dung lượng: </span>
            <strong style={{ color: "var(--text-primary)" }}>
              {formatBytes(docInfo?.size_bytes)}
            </strong>
          </div>

          <div>
            <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>Số trang: </span>
            <strong style={{ color: "var(--text-primary)" }}>
              {docInfo?.page_count ?? 1} trang
            </strong>
          </div>

          {isImage && docInfo?.width && docInfo?.height ? (
            <div>
              <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>Kích thước: </span>
              <strong style={{ color: "var(--text-primary)" }}>
                {docInfo.width} × {docInfo.height} px
              </strong>
            </div>
          ) : docInfo?.paragraph_count ? (
            <div>
              <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>Đoạn văn: </span>
              <strong style={{ color: "var(--text-primary)" }}>
                {docInfo.paragraph_count} đoạn
              </strong>
            </div>
          ) : docInfo?.line_count ? (
            <div>
              <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>Số dòng: </span>
              <strong style={{ color: "var(--text-primary)" }}>
                {docInfo.line_count} dòng
              </strong>
            </div>
          ) : null}
        </div>

        {ext === "pdf" && docInfo?.pdf_type && (
          <div
            style={{
              marginTop: "4px",
              padding: "6px 8px",
              backgroundColor: "var(--bg-surface)",
              borderRadius: "var(--radius-sm)",
              fontSize: "12px",
              color: "var(--text-secondary)",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <FileCheck size={14} style={{ color: "var(--accent-primary)" }} />
            <span>{getPdfTypeLabel(docInfo.pdf_type)}</span>
          </div>
        )}
      </div>
    </div>
  );
};
