import React, { useState, useMemo } from "react";
import { X, Folder, FileText, Image as ImageIcon, Check, Search } from "lucide-react";
import { FolderFileItem } from "../types/ipc";
import { formatBytes } from "../utils/fileUtils";

interface FolderFileModalProps {
  folderPath: string;
  files: FolderFileItem[];
  multiple?: boolean;
  onSelect: (selectedPaths: string[]) => void;
  onClose: () => void;
}

export const FolderFileModal: React.FC<FolderFileModalProps> = ({
  folderPath,
  files,
  multiple = false,
  onSelect,
  onClose,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedPaths, setSelectedPaths] = useState<string[]>([]);

  const filteredFiles = useMemo(() => {
    return files.filter((f) => {
      const matchSearch = f.name.toLowerCase().includes(searchTerm.toLowerCase());
      if (!matchSearch) return false;

      if (selectedCategory === "all") return true;
      if (selectedCategory === "pdf") return f.ext === "pdf";
      if (selectedCategory === "docx") return f.ext === "docx";
      if (selectedCategory === "txt") return ["txt", "md"].includes(f.ext);
      if (selectedCategory === "image") {
        return ["png", "jpg", "jpeg", "bmp", "webp", "tiff"].includes(f.ext);
      }
      return true;
    });
  }, [files, searchTerm, selectedCategory]);

  const toggleSelect = (path: string) => {
    if (!multiple) {
      onSelect([path]);
      onClose();
      return;
    }

    if (selectedPaths.includes(path)) {
      setSelectedPaths(selectedPaths.filter((p) => p !== path));
    } else {
      setSelectedPaths([...selectedPaths, path]);
    }
  };

  const handleSelectAll = () => {
    if (selectedPaths.length === filteredFiles.length) {
      setSelectedPaths([]);
    } else {
      setSelectedPaths(filteredFiles.map((f) => f.path));
    }
  };

  const handleConfirmMultiple = () => {
    if (selectedPaths.length > 0) {
      onSelect(selectedPaths);
      onClose();
    }
  };

  const getFormatColor = (ext: string) => {
    if (ext === "pdf") return "#ef4444";
    if (ext === "docx") return "#2563eb";
    if (["txt", "md"].includes(ext)) return "#059669";
    return "#f59e0b";
  };

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: "rgba(15, 23, 42, 0.55)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: "640px",
          maxHeight: "85vh",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
          padding: "20px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.15)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Folder size={20} style={{ color: "var(--accent-primary)" }} />
              <h3 style={{ fontSize: "17px", fontWeight: 600 }}>Chọn tài liệu trong thư mục</h3>
            </div>
            <div
              style={{
                fontSize: "12.5px",
                color: "var(--text-muted)",
                marginTop: "4px",
                maxWidth: "520px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              title={folderPath}
            >
              📁 {folderPath} • <strong>{files.length}</strong> tài liệu được tìm thấy
            </div>
          </div>
          <button
            type="button"
            className="btn-icon"
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-muted)",
              padding: "4px",
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Search & Category Filter */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "8px 12px",
              backgroundColor: "var(--bg-primary)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
            }}
          >
            <Search size={16} style={{ color: "var(--text-muted)" }} />
            <input
              type="text"
              placeholder="Tìm kiếm tài liệu theo tên..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                border: "none",
                background: "transparent",
                outline: "none",
                width: "100%",
                fontSize: "13.5px",
                color: "var(--text-primary)",
              }}
            />
          </div>

          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {[
              { id: "all", label: `Tất cả (${files.length})` },
              { id: "pdf", label: "PDF" },
              { id: "docx", label: "Word" },
              { id: "txt", label: "Text/MD" },
              { id: "image", label: "Ảnh" },
            ].map((cat) => (
              <button
                key={cat.id}
                type="button"
                className={`radio-btn ${selectedCategory === cat.id ? "active" : ""}`}
                style={{ padding: "4px 10px", fontSize: "12px" }}
                onClick={() => setSelectedCategory(cat.id)}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>

        {/* File List */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
            minHeight: "180px",
            maxHeight: "360px",
            padding: "4px 2px",
          }}
        >
          {filteredFiles.length === 0 ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "40px 20px",
                color: "var(--text-muted)",
                fontSize: "13.5px",
              }}
            >
              Không tìm thấy file tài liệu phù hợp trong thư mục này.
            </div>
          ) : (
            filteredFiles.map((file) => {
              const isSelected = selectedPaths.includes(file.path);
              const isImg = ["png", "jpg", "jpeg", "bmp", "webp", "tiff"].includes(file.ext);
              const color = getFormatColor(file.ext);

              return (
                <div
                  key={file.path}
                  onClick={() => toggleSelect(file.path)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    borderRadius: "var(--radius-md)",
                    backgroundColor: isSelected ? "var(--accent-light)" : "var(--bg-primary)",
                    border: `1px solid ${isSelected ? "var(--accent-primary)" : "var(--border-subtle)"}`,
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.backgroundColor = "var(--bg-hover)";
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) e.currentTarget.style.backgroundColor = "var(--bg-primary)";
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
                    {isImg ? (
                      <ImageIcon size={18} style={{ color, flexShrink: 0 }} />
                    ) : (
                      <FileText size={18} style={{ color, flexShrink: 0 }} />
                    )}
                    <div style={{ minWidth: 0 }}>
                      <div
                        style={{
                          fontSize: "13.5px",
                          fontWeight: 500,
                          color: "var(--text-primary)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                        title={file.name}
                      >
                        {file.name}
                      </div>
                      <div style={{ fontSize: "11.5px", color: "var(--text-muted)" }}>
                        {formatBytes(file.size_bytes)} • {file.ext.toUpperCase()}
                      </div>
                    </div>
                  </div>

                  {multiple ? (
                    <div
                      style={{
                        width: "18px",
                        height: "18px",
                        borderRadius: "4px",
                        border: `1.5px solid ${isSelected ? "var(--accent-primary)" : "var(--border-strong)"}`,
                        backgroundColor: isSelected ? "var(--accent-primary)" : "transparent",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#fff",
                      }}
                    >
                      {isSelected && <Check size={12} strokeWidth={3} />}
                    </div>
                  ) : (
                    <span
                      style={{
                        fontSize: "12px",
                        color: "var(--accent-primary)",
                        fontWeight: 600,
                      }}
                    >
                      Chọn file
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            display: "flex",
            justifyContent: multiple ? "space-between" : "flex-end",
            alignItems: "center",
            paddingTop: "10px",
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          {multiple && (
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: "13px" }}
              onClick={handleSelectAll}
            >
              {selectedPaths.length === filteredFiles.length ? "Bỏ chọn tất cả" : "Chọn tất cả"}
            </button>
          )}

          <div style={{ display: "flex", gap: "8px" }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Đóng
            </button>
            {multiple && (
              <button
                type="button"
                className="btn btn-primary"
                disabled={selectedPaths.length === 0}
                onClick={handleConfirmMultiple}
              >
                Xác nhận chọn ({selectedPaths.length})
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
