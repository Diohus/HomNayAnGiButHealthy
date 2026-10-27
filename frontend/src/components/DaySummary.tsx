import { useFoodNames } from "../api/hooks";
import { fmtPct, fmtSig } from "../format";
import { fmt, useI18n } from "../i18n";
import type { DayPlan } from "../types";
import { CalorieRing, MacroBar } from "./Progress";

export function DaySummary({ plan, eatenKcal }: { plan: DayPlan; eatenKcal?: number }) {
  const name = useFoodNames();
  const { t } = useI18n();
  const dev = Object.fromEntries(plan.deviations.map((d) => [d.code, d]));
  const e = dev.energy_kcal;
  const misses = plan.deviations.filter((d) => !d.within);
  return (
    <section className="card summary">
      {e && (eatenKcal !== undefined
        ? <CalorieRing actual={eatenKcal} target={e.target} planned={e.actual} />
        : <CalorieRing actual={e.actual} target={e.target} />)}
      <div className="macros">
        {["protein_g", "carb_g", "fat_g"].map((c) => dev[c] && (
          <MacroBar key={c} code={c} actual={dev[c].actual} target={dev[c].target} />
        ))}
      </div>
      {misses.length > 0 && (
        <div className="shortfalls">
          <strong>{t.today.shortfall}</strong>
          <ul>
            {misses.map((d) => {
              const s = plan.suggestions.find((x) => x.nutrient === d.code);
              return (
                <li key={d.code}>
                  {d.actual < d.target ? t.today.below : t.today.above} {t.nutrients[d.code] ?? d.code}: {fmtSig(d.actual)} /{" "}
                  {fmtSig(d.target)} ({fmtPct(d.pct)})
                  {s && s.food_codes.length > 0 && (
                    <span className="muted"> — {t.today.suggest}: {s.food_codes.map(name).join(", ")}</span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
      {plan.conflicts.length > 0 && (
        <p className="notice notice-warn">
          {fmt(t.today.conflicts, { list: plan.conflicts.map((c) => c.replace(/_/g, " ").toLowerCase()).join("; ") })}
        </p>
      )}
    </section>
  );
}
