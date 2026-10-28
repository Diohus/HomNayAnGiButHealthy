import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { NavLink } from "react-router-dom";
import { api } from "../api/client";
import { addDays, fmtGrams, fmtKcal, fmtSig, isoDay } from "../format";
import { fmt, useI18n } from "../i18n";
import type { WeekSummary } from "../types";

// "Hôm nay | Tuần" — the week view lives as a tab inside Today (the bottom nav already has 6 entries).
export function ViewSwitch() {
  const { t } = useI18n();
  return (
    <nav className="view-switch" aria-label={t.week.views}>
      <NavLink to="/" end>{t.nav.today}</NavLink>
      <NavLink to="/week">{t.nav.week}</NavLink>
    </nav>
  );
}

const UNITS: Record<string, string> = { fiber_g: "g", calcium_mg: "mg", iron_mg: "mg", zinc_mg: "mg", vitamin_d_ug: "µg" };
const W = 320, H = 160, PAD_B = 22, PAD_T = 8, BAR = 26;

function WeekChart({ w }: { w: WeekSummary }) {
  const { t, lang } = useI18n();
  const wd = new Intl.DateTimeFormat(lang === "vi" ? "vi-VN" : "en-GB", { weekday: "short" });
  const vals = w.days.map((d) => (w.basis === "eaten" ? d.eaten : d.planned)?.energy_kcal ?? null);
  const targets = w.days.map((d) => d.target.energy_kcal ?? 0);
  const max = Math.max(1, ...targets, ...vals.map((v) => v ?? 0)) * 1.1;
  const y = (v: number) => PAD_T + (H - PAD_T - PAD_B) * (1 - v / max);
  const step = W / 7;
  const label = (d: string) => wd.format(new Date(`${d}T00:00:00`));
  const what = w.basis === "eaten" ? t.week.eaten : t.week.planned;
  return (
    <>
      <svg viewBox={`0 0 ${W} ${H}`} className="week-chart" role="img"
           aria-label={fmt(t.week.chartLabel, { what })}>
        {w.days.map((d, i) => {
          const x = i * step + (step - BAR) / 2;
          const v = vals[i];
          return (
            <g key={d.day}>
              {v !== null && v > 0 && (
                <rect className="chart-bar" x={x} y={y(v)} width={BAR} height={H - PAD_B - y(v)} rx={4} />
              )}
              {v === null && <rect className="chart-empty" x={x} y={H - PAD_B - 4} width={BAR} height={4} rx={2} />}
              {targets[i] > 0 && (
                <line className="chart-target" x1={x - 4} x2={x + BAR + 4} y1={y(targets[i])} y2={y(targets[i])} />
              )}
              <text className="chart-label" x={x + BAR / 2} y={H - 6} textAnchor="middle">{label(d.day)}</text>
            </g>
          );
        })}
      </svg>
      <p className="small muted legend">
        <span className="swatch bar" /> {what} <span className="swatch target" /> {t.week.target}
      </p>
      <table className="sr-only">
        <caption>{fmt(t.week.chartLabel, { what })}</caption>
        <thead><tr><th>{t.week.day}</th><th>{what} (kcal)</th><th>{t.week.target} (kcal)</th></tr></thead>
        <tbody>
          {w.days.map((d, i) => (
            <tr key={d.day}>
              <td>{label(d.day)} {d.day}</td>
              <td>{vals[i] === null ? t.week.noData : fmtKcal(vals[i] as number)}</td>
              <td>{fmtKcal(targets[i])}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export function WeekPage() {
  const [end, setEnd] = useState(isoDay(new Date()));
  const { t, fmtDate } = useI18n();
  const q = useQuery({ queryKey: ["menu", "week", end], queryFn: () => api<WeekSummary>(`/summary/week?end=${end}`) });
  const w = q.data;
  const a = w?.average ?? {};
  const target = (code: string) => w?.days.find((d) => d.target[code])?.target[code] ?? 0;
  return (
    <main>
      <ViewSwitch />
      <div className="daynav">
        <button className="secondary" onClick={() => setEnd(addDays(end, -7))} aria-label={t.week.prev}>‹</button>
        <h2>{fmt(t.week.range, { from: fmtDate(addDays(end, -6)), to: fmtDate(end) })}</h2>
        <button className="secondary" onClick={() => setEnd(addDays(end, 7))} aria-label={t.week.next}>›</button>
      </div>
      {q.isError && <p className="error">{t.week.loadError}</p>}
      {w && (
        <>
          {w.basis === "planned" && <p className="notice small">{t.week.basisPlanned}</p>}
          <section className="card"><WeekChart w={w} /></section>
          {w.days_counted === 0 ? (
            <p className="card muted">{t.week.empty}</p>
          ) : (
            <section className="card">
              <h3>{fmt(t.week.averageTitle, { n: w.days_counted })}</h3>
              <p>{fmtKcal(a.energy_kcal ?? 0)} kcal · {t.macros.protein_g} {fmtGrams(a.protein_g ?? 0)} g · {t.macros.carb_g}{" "}
                {fmtGrams(a.carb_g ?? 0)} g · {t.macros.fat_g} {fmtGrams(a.fat_g ?? 0)} g · {t.macros.fiber_g}{" "}
                {fmtGrams(a.fiber_g ?? 0)} g</p>
              <p className="small muted">{fmt(t.week.within, { n: w.energy_within_days, of: w.days_counted })}</p>
            </section>
          )}
          {w.low_nutrients.length > 0 && (
            <section className="card">
              <h3>{t.week.lowTitle}</h3>
              <ul className="plain">
                {w.low_nutrients.map((x) => (
                  <li key={x.nutrient}>
                    <strong>{t.nutrients[x.nutrient] ?? x.nutrient}</strong>{" "}
                    {fmt(t.week.lowDays, { n: x.days_low })}
                    {x.suggestions.length > 0 && <> — {fmt(t.week.tryFoods, { foods: x.suggestions.map((s) => s.name).join(", ") })}</>}
                    {target(x.nutrient) > 0 && (
                      <span className="small muted"> ({fmt(t.week.avgVsTarget, {
                        avg: fmtSig(a[x.nutrient] ?? 0), target: fmtSig(target(x.nutrient)), unit: UNITS[x.nutrient] ?? "" })})</span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}
