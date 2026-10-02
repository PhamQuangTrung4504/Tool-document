import React, { useState, useEffect } from "react";
import { Sidebar, PageId } from "./components/Sidebar";
import { HomePage } from "./pages/HomePage";
import { ConvertPage } from "./pages/ConvertPage";
import { OCRPage } from "./pages/OCRPage";
import { MergePage } from "./pages/MergePage";
import { SplitPage } from "./pages/SplitPage";
import { HistoryPage } from "./pages/HistoryPage";
import { SettingsPage } from "./pages/SettingsPage";
import { tauriIpc } from "./services/tauriIpc";

export const App: React.FC = () => {
  const [activePage, setActivePage] = useState<PageId>("home");
  const [theme, setTheme] = useState<"light" | "dark" | "system">("light");
  const [backendReady, setBackendReady] = useState<boolean>(false);

  useEffect(() => {
    // Check initial backend status
    tauriIpc.getBackendStatus().then((status) => {
      setBackendReady(status.ready);
    });
  }, []);

  useEffect(() => {
    // Apply theme
    const root = document.documentElement;
    if (theme === "system") {
      const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      root.setAttribute("data-theme", prefersDark ? "dark" : "light");
    } else {
      root.setAttribute("data-theme", theme);
    }
  }, [theme]);

  const renderActivePage = () => {
    switch (activePage) {
      case "home":
        return <HomePage />;
      case "convert":
        return <ConvertPage />;
      case "ocr":
        return <OCRPage />;
      case "merge":
        return <MergePage />;
      case "split":
        return <SplitPage />;
      case "history":
        return <HistoryPage />;
      case "settings":
        return (
          <SettingsPage
            currentTheme={theme}
            onChangeTheme={setTheme}
          />
        );
      default:
        return <HomePage />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        activePage={activePage}
        onSelectPage={setActivePage}
        backendReady={backendReady}
      />
      <main className="main-content">{renderActivePage()}</main>
    </div>
  );
};

export default App;
