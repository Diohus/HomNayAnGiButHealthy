import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { addDays, isoDay } from "../format";
import { fmt, useI18n } from "../i18n";
import { checkedKey, loadChecked, purchaseText, saveChecked, shoppingText, type ShopLabels } from "../shopping";
import type { ShoppingList } from "../types";

export function ShoppingPage() {
  const { t, lang } = useI18n();
  const [start, setStart] = useState(isoDay(new Date()));
  const [days, setDays] = useState(3);
  const [servings, setServings] = useState(1);
  const [msg, setMsg] = useState<string | null>(null);
  const key = checkedKey(start, days);
  const [checked, setChecked] = useState<Set<string>>(() => loadChecked(key));
  useEffect(() => setChecked(loadChecked(key)), [key]);

  const list = useQuery({
    queryKey: ["shopping", start, days, servings, lang],
    queryFn: () => api<ShoppingList>(`/shopping-list?start=${start}&days=${days}&servings=${servings}`),
  });
  const labels: ShopLabels = {
    title: t.shopping.exportTitle, countUnits: t.shopping.countUnits, portion: t.shopping.portion,
    weight: t.shopping.weight,
  };
  const toggle = (code: string) => {
    const next = new Set(checked);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    setChecked(next);
    saveChecked(key, next);
  };
  const text = () => (list.data ? shoppingText(list.data, labels, checked) : "");
  async function copy() {
    try {
      await navigator.clipboard.writeText(text());
      setMsg(t.shopping.copied);
    } catch {
      setMsg(t.error);
    }
  }
  const canShare = typeof navigator !== "undefined" && typeof navigator.share === "function";

  return (
    <main>
      <h2>{t.shopping.title}</h2>
      <div className="card form grid3">
        <label>{t.shopping.start}<input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label>
        <label>{t.shopping.days}
          <select value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {[1, 2, 3, 4, 5, 6, 7].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        <label>{t.shopping.servings}
          <select value={servings} onChange={(e) => setServings(Number(e.target.value))}>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
      </div>
      {list.data && list.data.missing_days.length > 0 && (
        <p className="notice notice-warn">
          {fmt(t.shopping.missing, { days: list.data.missing_days.map((d) => d.slice(5)).join(", ") })}
        </p>
      )}
      {list.data?.groups.length === 0 && <p className="card small muted">{t.shopping.empty}</p>}
      {list.data?.groups.map((g) => (
        <section key={g.category} className="card">
          <h3>{g.label}</h3>
          <ul className="items">
            {g.items.map((it) => (
              <li key={it.code}>
                <label className="check">
                  <input type="checkbox" checked={checked.has(it.code)} onChange={() => toggle(it.code)} />
                  <span className={checked.has(it.code) ? "done" : ""}>{it.name}</span>
                </label>
                <span className="small">{purchaseText(it, labels)}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
      {list.data && list.data.groups.length > 0 && (
        <div className="card">
          <button type="button" onClick={copy}>{t.shopping.copy}</button>{" "}
          {canShare && (
            <button type="button" className="secondary"
                    onClick={() => navigator.share({ title: t.shopping.title, text: text() }).catch(() => undefined)}>
              {t.shopping.share}
            </button>
          )}
          {msg && <p className="small ok">{msg}</p>}
          <p className="small muted">{fmt(t.shopping.until, { end: addDays(start, days - 1) })}</p>
        </div>
      )}
    </main>
  );
}
