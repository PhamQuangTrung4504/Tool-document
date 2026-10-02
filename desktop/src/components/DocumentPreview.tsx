import React, { useEffect, useState } from "react";
import { FileText, Image as ImageIcon, Eye } from "lucide-react";
import { getFileExtension, getFileName } from "../utils/fileUtils";
import { tauriIpc } from "../services/tauriIpc";

interface DocumentPreviewProps {
  filePath: string;
}

export const DocumentPreview: React.FC<DocumentPreviewProps> = ({ filePath }) => {
  const ext = getFileExtension(filePath);
  const name = getFileName(filePath);
  const [docInfo, setDocInfo] = useState<{
    page_count?: number;
    size_bytes?: number;
    title?: string;
  } | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetchInfo = async () => {
      try {
        const res = await tauriIpc.executeIpc({
          operation: "info",
          input: filePath,
        });
        if (mounted && res.success && res.output && typeof res.output === "object") {
          const out = res.output as Record<string, unknown>;
          setDocInfo({
            page_count: out.page_count as number | undefined,
            size_bytes: out.size_bytes as number | undefined,
            title: out.title as string | undefined,
          });
        }
      } catch (err) {
        console.warn("Failed to fetch doc info:", err);
      }
    };

    fetchInfo();
    return () => {
      mounted = false;
    };
  }, [filePath]);

  const isImage = ["jpg", "jpeg", "png", "bmp"].includes(ext);

  return (
    <div
      className="card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        padding: "16px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <Eye size={16} style={{ color: "var(--accent-primary)" }} />
        <h4 style={{ fontSize: "14px", fontWeight: 600 }}>Xem trước thông tin</h4>
      </div>

      {isImage ? (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: "var(--bg-primary)",
            borderRadius: "var(--radius-md)",
            padding: "20px",
            minHeight: "140px",
          }}
        >
          <ImageIcon size={40} style={{ color: "var(--text-muted)", opacity: 0.6 }} />
          <span style={{ fontSize: "13px", marginTop: "8px", color: "var(--text-muted)" }}>
            Ảnh tài liệu: {name}
          </span>
        </div>
      ) : (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            backgroundColor: "var(--bg-primary)",
            padding: "14px",
            borderRadius: "var(--radius-md)",
            fontSize: "13px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <FileText size={18} style={{ color: "var(--accent-primary)" }} />
            <span style={{ fontWeight: 600 }}>{name}</span>
          </div>

          <div style={{ display: "flex", gap: "16px", color: "var(--text-muted)", marginTop: "4px" }}>
            <span>Định dạng: <strong style={{ color: "var(--text-primary)" }}>{ext.toUpperCase()}</strong></span>
            {docInfo?.page_count !== undefined && (
              <span>Số trang: <strong style={{ color: "var(--text-primary)" }}>{docInfo.page_count}</strong></span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
