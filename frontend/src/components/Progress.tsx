import { fmtGrams, fmtKcal } from "../format";
import { useI18n } from "../i18n";

export function CalorieRing({ actual, target }: { actual: number; target: number }) {
  const { t } = useI18n();
  const r = 54;
  const c = 2 * Math.PI * r;
  const ratio = target > 0 ? Math.min(actual / target, 1) : 0;
  const over = actual > target * 1.05;
  const left = target - actual;
  return (
    <div className="ring" role="img" aria-label={`${fmtKcal(actual)} / ${fmtKcal(target)} kcal`}>
      <svg viewBox="0 0 128 128" width="148" height="148">
        <circle cx="64" cy="64" r={r} className="ring-track" />
        <circle cx="64" cy="64" r={r} className={over ? "ring-over" : "ring-fill"} strokeDasharray={c}
                strokeDashoffset={c * (1 - ratio)} transform="rotate(-90 64 64)" />
      </svg>
      <div className="ring-label">
        <strong>{fmtKcal(Math.abs(left))}</strong>
        <span>kcal {left >= 0 ? t.today.remaining : t.today.over}</span>
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
