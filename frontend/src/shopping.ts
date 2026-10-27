import type { ShoppingItem, ShoppingList } from "./types";

export interface ShopLabels {
  title: string; // "{days} ngày × {servings} người, từ {start}"
  countUnits: Record<string, string>; // unit_key → "{n} quả"
  portion: string; // "{n} × {portion}"
  weight: string; // "{grams} g"
}

const fill = (s: string, v: Record<string, string | number>) =>
  s.replace(/\{(\w+)\}/g, (m, k: string) => (v[k] === undefined ? m : String(v[k])));

export function purchaseText(it: ShoppingItem, l: ShopLabels): string {
  const p = it.purchase;
  if (p.kind === "count") return fill(l.countUnits[p.unit_key ?? ""] ?? l.weight, { n: p.count ?? 0, grams: p.grams });
  if (p.kind === "portion") return fill(l.portion, { n: p.count ?? 0, portion: p.portion ?? "" });
  return fill(l.weight, { grams: p.grams });
}

/** Plain text for copy / Web Share: groups by category, one line per item, checked items marked ✓. */
export function shoppingText(list: ShoppingList, l: ShopLabels, checked: Set<string> = new Set()): string {
  const lines = [fill(l.title, { days: list.days, servings: list.servings, start: list.start })];
  for (const g of list.groups) {
    lines.push("", `${g.label}:`);
    for (const it of g.items) lines.push(`${checked.has(it.code) ? "✓" : "-"} ${it.name}: ${purchaseText(it, l)}`);
  }
  return lines.join("\n");
}

export function checkedKey(start: string, days: number): string {
  return `hnag_shop_${start}_${days}`;
}

export function loadChecked(key: string): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(key) ?? "[]") as string[]);
  } catch {
    return new Set();
  }
}

export function saveChecked(key: string, codes: Set<string>): void {
  try {
    localStorage.setItem(key, JSON.stringify([...codes]));
  } catch {
    /* storage blocked: the checklist just isn't remembered */
  }
}
