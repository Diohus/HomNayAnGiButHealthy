import { fmtGrams, fmtKcal } from "../format";
import { fmt, useI18n } from "../i18n";

// actual = eaten so far; planned (optional) = the whole day's plan, drawn faintly behind.
export function CalorieRing({ actual, target, planned }: { actual: number; target: number; planned?: number }) {
  const { t } = useI18n();
  const r = 54;
  const c = 2 * Math.PI * r;
  const ratio = target > 0 ? Math.min(actual / target, 1) : 0;
  const plannedRatio = target > 0 && planned !== undefined ? Math.min(planned / target, 1) : 0;
  const over = actual > target * 1.05;
  const left = target - actual;
  const label = planned !== undefined
    ? fmt(t.today.ringAria, { eaten: fmtKcal(actual), target: fmtKcal(target), planned: fmtKcal(planned) })
    : `${fmtKcal(actual)} / ${fmtKcal(target)} kcal`;
  return (
    <div className="ring" role="img" aria-label={label}>
      <svg viewBox="0 0 128 128" width="148" height="148">
        <circle cx="64" cy="64" r={r} className="ring-track" />
        {planned !== undefined && (
          <circle cx="64" cy="64" r={r} className="ring-planned" strokeDasharray={c}
                  strokeDashoffset={c * (1 - plannedRatio)} transform="rotate(-90 64 64)" />
        )}
        <circle cx="64" cy="64" r={r} className={over ? "ring-over" : "ring-fill"} strokeDasharray={c}
                strokeDashoffset={c * (1 - ratio)} transform="rotate(-90 64 64)" />
      </svg>
      <div className="ring-label">
        <strong>{fmtKcal(Math.abs(left))}</strong>
        <span>kcal {left >= 0 ? t.today.remaining : t.today.over}</span>
        {planned !== undefined && <span>{fmt(t.today.eatenOf, { eaten: fmtKcal(actual), target: fmtKcal(target) })}</span>}
      </div>
    </div>
  );
}

export function MacroBar({ code, actual, target }: { code: string; actual: number; target: number }) {
  const { t } = useI18n();
  const pct = target > 0 ? Math.min((actual / target) * 100, 100) : 0;
  return (
    <div className="macro">
      <div className="macro-head">
        <span>{t.macros[code] ?? code}</span>
        <span className="muted">{fmtGrams(actual)} / {fmtGrams(target)} g</span>
      </div>
      <div className="bar"><div className={`bar-fill m-${code}`} style={{ width: `${pct}%` }} /></div>
    </div>
  );
}
