import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import type { MenuDay } from "../types";
import { applyMenuResult, menusFromResult } from "./hooks";

const md = (day: string, version = 2) => ({ day, version, plan: { meals: [] } }) as unknown as MenuDay;

describe("menusFromResult", () => {
  it("MenuDay, MenuDay[] (generate), { menu } (chat apply); còn lại ⇒ rỗng", () => {
    expect(menusFromResult(md("2026-10-28")).map((m) => m.day)).toEqual(["2026-10-28"]);
    expect(menusFromResult([md("2026-10-28")])).toHaveLength(1);
    expect(menusFromResult({ day: "2026-10-28", menu: md("2026-10-28") })).toHaveLength(1);
    expect(menusFromResult({ day: null, menu: null })).toEqual([]);
    expect(menusFromResult({ steps: [], tip: "" })).toEqual([]); // recipe
    expect(menusFromResult(undefined)).toEqual([]);
  });
});

describe("applyMenuResult", () => {
  it("ghi MenuDay vào cache ngày đó (không invalidate), chỉ invalidate các query menu khác", async () => {
    const qc = new QueryClient();
    qc.setQueryData(["menu", "2026-10-28"], [md("2026-10-28", 1)]);
    qc.setQueryData(["menu", "2026-10-29"], [md("2026-10-29", 1)]);
    qc.setQueryData(["menu", "week", "2026-10-28"], { end: "2026-10-28" });
    await applyMenuResult(qc, md("2026-10-28", 5));
    expect(qc.getQueryData<MenuDay[]>(["menu", "2026-10-28"])?.[0].version).toBe(5);
    expect(qc.getQueryState(["menu", "2026-10-28"])?.isInvalidated).toBe(false);
    expect(qc.getQueryState(["menu", "2026-10-29"])?.isInvalidated).toBe(true);
    expect(qc.getQueryState(["menu", "week", "2026-10-28"])?.isInvalidated).toBe(true);
  });

  it("kết quả không có MenuDay (recipe) ⇒ invalidate mọi query menu", async () => {
    const qc = new QueryClient();
    qc.setQueryData(["menu", "2026-10-28"], [md("2026-10-28", 1)]);
    await applyMenuResult(qc, { steps: [] });
    expect(qc.getQueryState(["menu", "2026-10-28"])?.isInvalidated).toBe(true);
  });
});
