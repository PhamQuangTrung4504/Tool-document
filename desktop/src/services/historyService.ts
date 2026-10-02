import { HistoryItem } from "../types/history";

const HISTORY_STORAGE_KEY = "doc_assistant_history_v1";
const MAX_HISTORY_ITEMS = 100;

export const historyService = {
  getHistory(): HistoryItem[] {
    try {
      const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  },

  addEntry(item: Omit<HistoryItem, "id">): HistoryItem {
    const list = this.getHistory();
    const newEntry: HistoryItem = {
      ...item,
      id: "hist_" + Date.now() + "_" + Math.random().toString(36).substring(2, 7),
    };

    const updated = [newEntry, ...list].slice(0, MAX_HISTORY_ITEMS);
    try {
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(updated));
    } catch (e) {
      console.error("Failed to save history to localStorage:", e);
    }
    return newEntry;
  },

  removeEntry(id: string): void {
    const list = this.getHistory();
    const updated = list.filter((item) => item.id !== id);
    try {
      localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(updated));
    } catch (e) {
      console.error("Failed to update history in localStorage:", e);
    }
  },

  clearHistory(): void {
    try {
      localStorage.removeItem(HISTORY_STORAGE_KEY);
    } catch (e) {
      console.error("Failed to clear history in localStorage:", e);
    }
  },
};
