// Chế độ giao diện. public/theme-init.js áp dụng trước khi React render (chống nháy) — giữ hai file cùng logic.
export type Theme = "system" | "light" | "dark";
export const THEMES: Theme[] = ["system", "light", "dark"];
const KEY = "hnag_theme";
// Khớp --bg trong styles.css (thanh trạng thái/thanh địa chỉ trên di động)
const THEME_COLOR = { light: "#f6f7f9", dark: "#0f1218" } as const;

function isTheme(v: unknown): v is Theme {
  return typeof v === "string" && (THEMES as string[]).includes(v);
}

export function getTheme(): Theme {
  try {
    const v = localStorage.getItem(KEY);
    return isTheme(v) ? v : "system";
  } catch {
    return "system";
  }
}

function systemDark(): boolean {
  try {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  } catch {
    return false;
  }
}

export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (theme === "system") delete root.dataset.theme;
  else root.dataset.theme = theme;
  const meta = document.querySelector('meta[name="theme-color"]');
  const effective = theme === "system" ? (systemDark() ? "dark" : "light") : theme;
  meta?.setAttribute("content", THEME_COLOR[effective]);
}

export function setTheme(theme: Theme): void {
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    /* trình duyệt chặn storage: vẫn áp dụng cho phiên hiện tại */
  }
  applyTheme(theme);
}
