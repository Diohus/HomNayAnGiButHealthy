import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { applyTheme, getTheme, setTheme } from "./theme";

// Môi trường node: giả lập tối thiểu document/localStorage/matchMedia (không thêm jsdom).
function fakeStorage(): Storage {
  const m = new Map<string, string>();
  return {
    getItem: (k) => m.get(k) ?? null, setItem: (k, v) => void m.set(k, String(v)), removeItem: (k) => void m.delete(k),
    clear: () => m.clear(), key: (i) => [...m.keys()][i] ?? null, get length() { return m.size; },
  };
}
const throwingStorage = {
  getItem: () => { throw new Error("SecurityError"); },
  setItem: () => { throw new Error("QuotaExceededError"); },
  removeItem: () => { throw new Error("SecurityError"); },
};

let meta: { content: string; setAttribute: (k: string, v: string) => void };
let root: { dataset: Record<string, string | undefined> };

beforeEach(() => {
  meta = { content: "", setAttribute(_k, v) { this.content = v; } };
  root = { dataset: {} };
  vi.stubGlobal("document", { documentElement: root, querySelector: () => meta });
  vi.stubGlobal("window", { matchMedia: () => ({ matches: false }) });
  vi.stubGlobal("localStorage", fakeStorage());
});
afterEach(() => vi.unstubAllGlobals());

describe("theme", () => {
  it("mặc định theo hệ thống", () => expect(getTheme()).toBe("system"));

  it("lưu và đọc lại lựa chọn", () => {
    setTheme("dark");
    expect(localStorage.getItem("hnag_theme")).toBe("dark");
    expect(getTheme()).toBe("dark");
    setTheme("light");
    expect(getTheme()).toBe("light");
  });

  it("giá trị lạ trong storage ⇒ system", () => {
    localStorage.setItem("hnag_theme", "purple");
    expect(getTheme()).toBe("system");
  });

  it("đặt data-theme cho light/dark và xóa khi system", () => {
    setTheme("dark");
    expect(root.dataset.theme).toBe("dark");
    expect(meta.content).toBe("#0f1218");
    setTheme("light");
    expect(root.dataset.theme).toBe("light");
    setTheme("system");
    expect("theme" in root.dataset).toBe(false);
    expect(meta.content).toBe("#f6f7f9"); // hệ thống đang sáng
  });

  it("system theo prefers-color-scheme cho meta theme-color", () => {
    vi.stubGlobal("window", { matchMedia: () => ({ matches: true }) });
    applyTheme("system");
    expect(meta.content).toBe("#0f1218");
  });

  it("storage ném lỗi vẫn chạy", () => {
    vi.stubGlobal("localStorage", throwingStorage);
    expect(getTheme()).toBe("system");
    expect(() => setTheme("dark")).not.toThrow();
    expect(root.dataset.theme).toBe("dark");
  });
});
