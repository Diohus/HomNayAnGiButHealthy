import { afterEach, describe, expect, it, vi } from "vitest";
import { checkedKey, loadChecked, purchaseText, saveChecked, shoppingText, type ShopLabels } from "./shopping";
import type { ShoppingList } from "./types";

const L: ShopLabels = {
  title: "Đi chợ {days} ngày × {servings} người, từ {start}",
  countUnits: { egg: "{n} quả" },
  portion: "{n} × {portion}",
  weight: "{grams} g",
};

const LIST: ShoppingList = {
  start: "2026-10-21", days: 3, servings: 2, missing_days: [],
  groups: [
    { category: "protein", label: "Thịt, cá, trứng", items: [
      { code: "egg", name: "Trứng gà", grams: 120, days_used: ["2026-10-21"],
        purchase: { kind: "count", count: 3, unit_key: "egg", grams: 150 } },
      { code: "salmon", name: "Cá hồi", grams: 260, days_used: ["2026-10-22"], purchase: { kind: "weight", grams: 300 } },
    ] },
    { category: "snack", label: "Đồ ăn vặt", items: [
      { code: "cola", name: "Cola", grams: 370, days_used: ["2026-10-21"],
        purchase: { kind: "portion", count: 1, portion: "1 can", grams: 370 } },
    ] },
  ],
};

describe("danh sách đi chợ dạng văn bản", () => {
  it("định dạng đơn vị mua", () => {
    const [egg, salmon] = LIST.groups[0].items;
    expect(purchaseText(egg, L)).toBe("3 quả");
    expect(purchaseText(salmon, L)).toBe("300 g");
    expect(purchaseText(LIST.groups[1].items[0], L)).toBe("1 × 1 can");
  });

  it("xuất văn bản nhóm theo loại, đánh dấu món đã mua", () => {
    expect(shoppingText(LIST, L, new Set(["salmon"]))).toBe([
      "Đi chợ 3 ngày × 2 người, từ 2026-10-21", "", "Thịt, cá, trứng:", "- Trứng gà: 3 quả", "✓ Cá hồi: 300 g",
      "", "Đồ ăn vặt:", "- Cola: 1 × 1 can",
    ].join("\n"));
  });
});

describe("đánh dấu đã mua (localStorage)", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("lưu/đọc theo khóa (start, days)", () => {
    const m = new Map<string, string>();
    vi.stubGlobal("localStorage", { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => m.set(k, v) });
    const key = checkedKey("2026-10-21", 3);
    saveChecked(key, new Set(["egg"]));
    expect([...loadChecked(key)]).toEqual(["egg"]);
    expect(loadChecked(checkedKey("2026-10-21", 2)).size).toBe(0);
  });

  it("storage ném lỗi vẫn chạy", () => {
    vi.stubGlobal("localStorage", { getItem: () => { throw new Error("x"); }, setItem: () => { throw new Error("x"); } });
    expect(loadChecked("k").size).toBe(0);
    expect(() => saveChecked("k", new Set(["a"]))).not.toThrow();
  });
});
