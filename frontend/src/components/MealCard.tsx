import { useState } from "react";
import { useFoodNames } from "../api/hooks";
import { fmtGrams, fmtKcal } from "../format";
import { fmt, useI18n } from "../i18n";
import type { MealPlan, Recipe } from "../types";

interface Props {
  meal: MealPlan;
  dishName: string | null;
  recipe?: Recipe;
  busy: boolean;
  onAdjust?: (food: string, delta: number) => void;
  onUnlock?: (food: string) => void;
  onRecipe?: () => void;
  onSwap?: () => void;
  eaten?: boolean;
  onEaten?: (eaten: boolean) => void;
  usedDisliked?: boolean;
}

export function MealCard({ meal, dishName, recipe, busy, onAdjust, onUnlock, onRecipe, onSwap, eaten, onEaten,
                          usedDisliked }: Props) {
  const [open, setOpen] = useState(meal.slot !== "snack");
  const name = useFoodNames();
  const { t } = useI18n();
  const tag = (origin: string) =>
    origin === "pantry" ? t.today.tags.pantry : origin === "snack" ? t.today.tags.snack
      : origin === "ai_estimate" ? t.today.tags.aiEstimate : t.today.tags.adjusted;
  return (
    <section className={`card meal${eaten ? " eaten" : ""}`}>
      <button className="meal-head" onClick={() => setOpen(!open)} aria-expanded={open}>
        <div>
          <h3>{t.slots[meal.slot] ?? meal.slot}</h3>
          {dishName && <span className="muted">{dishName}</span>}
        </div>
        <span className="kcal">{fmtKcal(meal.totals.energy_kcal ?? 0)} kcal</span>
      </button>
      {onEaten && (
        <label className="check small">
          <input type="checkbox" checked={!!eaten} disabled={busy} onChange={(e) => onEaten(e.target.checked)} />
          {t.today.eaten}
        </label>
      )}
      {usedDisliked && <p className="notice notice-warn small">{t.today.usedDisliked}</p>}
      {open && (
        <>
          <ul className="items">
            {meal.items.map((it) => (
              <li key={it.food_code}>
                <span className="item-name">
                  {name(it.food_code)}
                  {it.locked && <span className="tag">{tag(it.origin)}</span>}
                </span>
                <span className="item-ctl">
                  {onAdjust && it.origin !== "pantry" && (
                    <button aria-label={fmt(t.today.decrease, { name: name(it.food_code) })} disabled={busy} onClick={() => onAdjust(it.food_code, -10)}>−</button>
                  )}
                  <span className="grams">{fmtGrams(it.grams)} g</span>
                  {onAdjust && it.origin !== "pantry" && (
                    <button aria-label={fmt(t.today.increase, { name: name(it.food_code) })} disabled={busy} onClick={() => onAdjust(it.food_code, 10)}>+</button>
                  )}
                  {onUnlock && it.locked && it.origin === "user_adjust" && (
                    <button className="link" disabled={busy} onClick={() => onUnlock(it.food_code)}>{t.today.unlock}</button>
                  )}
                </span>
              </li>
            ))}
          </ul>
          <p className="muted small">
            {t.macros.protein_g} {fmtGrams(meal.totals.protein_g ?? 0)} g · {t.macros.carb_g}{" "}
            {fmtGrams(meal.totals.carb_g ?? 0)} g · {t.macros.fat_g} {fmtGrams(meal.totals.fat_g ?? 0)} g
          </p>
          {onRecipe && meal.slot !== "snack" && (
            <button className="secondary" disabled={busy} onClick={onRecipe}>{t.today.recipe}</button>
          )}
          {onSwap && meal.slot !== "snack" && (
            <button className="secondary" disabled={busy} onClick={onSwap}
                    aria-label={`${t.today.swap} — ${t.slots[meal.slot] ?? meal.slot}`}>{t.today.swap}</button>
          )}
          {recipe && (
            <div className="recipe">
              <ol>{recipe.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
              {recipe.seasonings.length > 0 && (
                <p className="small">
                  {fmt(t.today.seasonings, { list: recipe.seasonings.map((s) => `${s.name} (${s.note})`).join(", ") })}
                </p>
              )}
              {recipe.tip && <p className="small muted">{recipe.tip}</p>}
              <p className="small muted">{recipe.source === "llm" ? t.today.sourceLlm : t.today.sourceTemplate}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
