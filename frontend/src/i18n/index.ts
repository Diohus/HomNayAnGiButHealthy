import { createContext, createElement, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ApiError, setApiLang } from "../api/client";
import { en } from "./en";
import { vi, type Dict } from "./vi";

export type Lang = "vi" | "en";
export type { Dict };
export const LANGS: Lang[] = ["vi", "en"];
// Tên ngôn ngữ luôn hiển thị bằng chính ngôn ngữ đó
export const LANG_NAMES: Record<Lang, string> = { vi: "Tiếng Việt", en: "English" };
export const dictionaries: Record<Lang, Dict> = { vi, en };
const KEY = "hnag_lang";

export function getLang(): Lang {
  try {
    const v = localStorage.getItem(KEY);
    return v === "en" || v === "vi" ? v : "vi";
  } catch {
    return "vi";
  }
}

function storeLang(lang: Lang) {
  try {
    localStorage.setItem(KEY, lang);
  } catch {
    /* trình duyệt chặn storage: chỉ áp dụng cho phiên hiện tại */
  }
}

/** Điền placeholder {ten} trong chuỗi từ điển. */
export function fmt(s: string, vars: Record<string, string | number | undefined>): string {
  return s.replace(/\{(\w+)\}/g, (m, k: string) => (vars[k] === undefined ? m : String(vars[k])));
}

/** Thông báo lỗi theo ngôn ngữ: t.errors[code] (điền {x} từ body và body.params — backend đã dịch params theo
 * Accept-Language), không có thì dùng message của server. */
export function errorMessage(x: unknown, t: Dict): string {
  if (!(x instanceof ApiError)) return t.error;
  const fields = (x.body.errors as { field: string; message: string }[] | undefined) ?? [];
  // Backend dịch thông điệp từng trường theo Accept-Language ⇒ hiển thị chi tiết ở cả hai ngôn ngữ
  if (x.code === "VALIDATION_ERROR" && fields.length) return fields.map((e) => e.message).join("; ");
  const params = (x.body.params as Record<string, string | number> | undefined) ?? {};
  const vars = { ...(x.body as Record<string, string | number>), ...params };
  let tpl = t.errors[x.code] ?? (x.code.startsWith("HTTP_") ? t.errors.HTTP : undefined);
  // E10: ALLERGEN_CONFLICT có params ⇒ câu cụ thể (tên nguyên liệu + lý do đã dịch)
  if (x.code === "ALLERGEN_CONFLICT" && params.reason) {
    tpl = params.food ? t.errors.ALLERGEN_CONFLICT_ITEM : t.errors.ALLERGEN_CONFLICT_CUSTOM;
  }
  if (tpl) return fmt(tpl, vars);
  return x.message || t.error;
}

interface I18n {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: Dict;
  fmtDate: (iso: string) => string;
}

const Ctx = createContext<I18n | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    const l = getLang();
    setApiLang(l);
    return l;
  });
  const setLang = useCallback((l: Lang) => {
    storeLang(l);
    setApiLang(l);
    setLangState(l);
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = dictionaries[lang].appName;
  }, [lang]);
  const value = useMemo<I18n>(() => {
    const df = new Intl.DateTimeFormat(lang === "vi" ? "vi-VN" : "en-US",
                                       { weekday: "short", day: "numeric", month: "numeric", year: "numeric" });
    return { lang, setLang, t: dictionaries[lang], fmtDate: (iso) => df.format(new Date(`${iso}T00:00:00`)) };
  }, [lang, setLang]);
  return createElement(Ctx.Provider, { value }, children);
}

export function useI18n(): I18n {
  const v = useContext(Ctx);
  if (!v) throw new Error("useI18n phải nằm trong <I18nProvider>");
  return v;
}
