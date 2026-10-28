import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, del, post } from "../api/client";
import { useFoodNames, useFoods } from "../api/hooks";
import { isoDay } from "../format";
import { HelpLink } from "../components/Help";
import { errorMessage, fmt, useI18n } from "../i18n";

export function PantryPage() {
  const [day, setDay] = useState(isoDay(new Date()));
  const [food, setFood] = useState("");
  const [grams, setGrams] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const foods = useFoods();
  const name = useFoodNames();
  const qc = useQueryClient();
  const { t, lang } = useI18n();
  const items = useQuery({
    queryKey: ["pantry", day],
    queryFn: () => api<{ id: number; food_code: string; grams: number }[]>(`/pantry?day=${day}`),
  });
  const allowed = (foods.data ?? []).filter((f) => !f.excluded_reason)
    .map((f) => ({ ...f, label: name(f.code) }))
    .sort((a, b) => a.label.localeCompare(b.label, lang));

  async function add(e: React.FormEvent) {
    e.preventDefault();
    try {
      const r = await post<{ warnings: string[] }>("/pantry", { day, food_code: food, grams: Number(grams) });
      setMsg(r.warnings.includes("PANTRY_EXCEEDS_ENERGY")
        ? { ok: false, text: t.pantry.exceeds }
        : { ok: true, text: t.pantry.added });
      setGrams("");
      qc.invalidateQueries({ queryKey: ["pantry", day] });
    } catch (x) {
      setMsg({ ok: false, text: errorMessage(x, t) });
    }
  }

  return (
    <main>
      <h2>{t.pantry.title}</h2>
      <p><HelpLink section="pantry" /></p>
      <form className="card form" onSubmit={add}>
        <label>{t.pantry.day}<input type="date" value={day} onChange={(e) => setDay(e.target.value)} /></label>
        <label>{t.pantry.food}
          <select value={food} onChange={(e) => setFood(e.target.value)} required>
            <option value="">—</option>
            {allowed.map((f) => (
              <option key={f.code} value={f.code}>{f.label}{f.user_provided ? ` (${t.userProvided})` : ""}</option>
            ))}
          </select>
        </label>
        <label>{t.pantry.grams}<input type="number" min="1" max="3000" value={grams} onChange={(e) => setGrams(e.target.value)} required /></label>
        {msg && <p className={msg.ok ? "ok" : "error"}>{msg.text}</p>}
        <button type="submit">{t.pantry.add}</button>
      </form>
      <ul className="card items">
        {(items.data ?? []).map((i) => (
          <li key={i.id}>
            <span>{name(i.food_code)}</span>
            <span className="item-ctl">
              <span className="grams">{Math.round(i.grams)} g</span>
              <button className="link" aria-label={fmt(t.pantry.removeItem, { name: name(i.food_code) })}
                      onClick={async () => { await del(`/pantry/${i.id}`); qc.invalidateQueries({ queryKey: ["pantry", day] }); }}>
                {t.pantry.remove}
              </button>
            </span>
          </li>
        ))}
      </ul>
    </main>
  );
}
