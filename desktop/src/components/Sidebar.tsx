import React from "react";
import {
  FileText,
  ScanText,
  Files,
  Scissors,
  History,
  Settings,
  Home,
  FileCode2,
} from "lucide-react";

export type PageId =
  | "home"
  | "convert"
  | "ocr"
  | "merge"
  | "split"
  | "history"
  | "settings";

interface SidebarProps {
  activePage: PageId;
  onSelectPage: (page: PageId) => void;
  backendReady: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activePage,
  onSelectPage,
  backendReady,
}) => {
  const navItems: { id: PageId; label: string; icon: React.ReactNode }[] = [
    { id: "home", label: "Trang chủ", icon: <Home size={18} /> },
    { id: "convert", label: "Chuyển đổi", icon: <FileText size={18} /> },
    { id: "ocr", label: "Nhận diện OCR", icon: <ScanText size={18} /> },
    { id: "merge", label: "Ghép PDF", icon: <Files size={18} /> },
    { id: "split", label: "Tách PDF", icon: <Scissors size={18} /> },
    { id: "history", label: "Lịch sử", icon: <History size={18} /> },
    { id: "settings", label: "Cài đặt", icon: <Settings size={18} /> },
  ];

  return (
    <aside className="sidebar">
      <div>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <FileCode2 size={18} />
          </div>
          <div>
            <div className="sidebar-title">Doc Assistant</div>
            <div style={{ fontSize: "11px", color: "var(--text-muted)" }}>
              Windows Offline
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <button
              key={item.id}
              className={`nav-item ${activePage === item.id ? "active" : ""}`}
              onClick={() => onSelectPage(item.id)}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      <div className="sidebar-footer">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "12px",
            color: "var(--text-muted)",
          }}
        >
          <span
            style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              backgroundColor: backendReady ? "#10b981" : "#f59e0b",
            }}
          />
          <span>{backendReady ? "Backend: Sẵn sàng" : "Backend: Đang kết nối"}</span>
        </div>
      </div>
    </aside>
  );
};
