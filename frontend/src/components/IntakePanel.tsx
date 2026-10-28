import { useState } from "react";
import { del, post } from "../api/client";
import { useFoodNames, useFoods } from "../api/hooks";
import { fmtGrams, foldText } from "../format";
import { errorMessage, fmt, useI18n } from "../i18n";
import type { MenuDay } from "../types";
import { PhotoIntake } from "./PhotoIntake";

const SLOTS = ["breakfast", "lunch", "dinner", "snack"];

// Off-plan intake for the day: list (with delete), quick add (search + grams + meal), and "rebalance remaining".
export function IntakePanel({ md, day, busy, onChanged, onRebalance }: {
  md: MenuDay; day: string; busy: boolean; onChanged: () => void; onRebalance: () => void;
}) {
  const { t } = useI18n();
  const foods = useFoods();
  const name = useFoodNames();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [code, setCode] = useState<string | null>(null);
  const [grams, setGrams] = useState("100");
  const [slot, setSlot] = useState("snack");
  const [err, setErr] = useState<string | null>(null);

  const offPlan = md.intake.entries.filter((e) => e.source !== "plan");
  const eatenKcal = md.intake.totals.energy_kcal ?? 0;
  const target = md.plan.deviations.find((d) => d.code === "energy_kcal")?.target ?? 0;
  const plannedRest = md.plan.meals.filter((m) => m.slot !== "snack" && !md.eaten_slots.includes(m.slot))
    .reduce((a, m) => a + (m.totals.energy_kcal ?? 0), 0);
  const projected = eatenKcal + plannedRest;
  const showRebalance = target > 0 && (offPlan.length > 0 || md.eaten_slots.length > 0)
    && Math.abs(projected - target) / target > 0.05;

  const needle = foldText(q.trim());
  const results = needle ? (foods.data ?? []).filter((f) => !f.excluded_reason && foldText(name(f.code)).includes(needle))
    .slice(0, 6) : [];

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!code) return;
    setErr(null);
    try {
      await post("/intake", { day, slot, food_code: code, grams: Number(grams) });
      setQ("");
      setCode(null);
      setOpen(false);
      onChanged();
    } catch (x) {
      setErr(errorMessage(x, t));
    }
  }
  async function remove(id: number) {
    try {
      await del(`/intake/${id}`);
      onChanged();
    } catch (x) {
      setErr(errorMessage(x, t));
    }
  }

  return (
    <section className="card">
      <h3>{t.intake.offPlan}</h3>
      {offPlan.length === 0 && <p className="small muted">{t.intake.none}</p>}
      <ul className="items">
        {offPlan.map((e) => (
          <li key={e.id}>
            <span>{name(e.food_code)} <span className="small muted">· {t.slots[e.slot] ?? e.slot}</span>
              {e.source === "ai_estimate" && <span className="tag">{t.today.tags.aiEstimate}</span>}
              {e.source === "estimate" && <span className="tag">{t.today.tags.estimate}</span>}</span>
            <span className="item-ctl">
              <span className="grams">{fmtGrams(e.grams)} g</span>
              <button className="link" aria-label={fmt(t.pantry.removeItem, { name: name(e.food_code) })}
                      onClick={() => remove(e.id)}>{t.pantry.remove}</button>
            </span>
          </li>
        ))}
      </ul>
      {open ? (
        <form className="form" onSubmit={add}>
          <label>{t.intake.search}
            <input type="search" value={q} onChange={(e) => { setQ(e.target.value); setCode(null); }} />
          </label>
          {!code && results.length > 0 && (
            <ul className="items">
              {results.map((f) => (
                <li key={f.code}>
                  <span>{name(f.code)}</span>
                  <button type="button" className="link" onClick={() => { setCode(f.code); setQ(name(f.code)); }}>
                    {t.intake.choose}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="grid3">
            <label>{t.pantry.grams}
              <input type="number" min="1" max="3000" value={grams} onChange={(e) => setGrams(e.target.value)} required />
            </label>
            <label>{t.intake.meal}
              <select value={slot} onChange={(e) => setSlot(e.target.value)}>
                {SLOTS.map((s) => <option key={s} value={s}>{t.slots[s]}</option>)}
              </select>
            </label>
          </div>
          {err && <p className="error">{err}</p>}
          <button type="submit" disabled={!code}>{t.intake.add}</button>
          <button type="button" className="link" onClick={() => setOpen(false)}>{t.limits.cancel}</button>
        </form>
      ) : (
        <>
          <button className="secondary" onClick={() => setOpen(true)}>{t.intake.addOpen}</button>{" "}
          <PhotoIntake day={day} onSaved={onChanged} />
        </>
      )}
      {showRebalance && (
        <div className="notice notice-warn">
          <p className="small">{fmt(t.intake.diff, { projected: Math.round(projected / 10) * 10,
                                                     target: Math.round(target / 10) * 10 })}</p>
          <button disabled={busy} onClick={onRebalance}>{t.intake.rebalance}</button>
        </div>
      )}
    </section>
  );
}
