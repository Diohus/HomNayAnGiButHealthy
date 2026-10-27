import { useState } from "react";
import { post } from "../api/client";
import { generateDay, useDishNames, useMenu, useMenuMutation, useNeeds } from "../api/hooks";
import { DaySummary } from "../components/DaySummary";
import { MealCard } from "../components/MealCard";
import { Notices } from "../components/Notices";
import { addDays, isoDay } from "../format";
import { errorMessage, fmt, useI18n } from "../i18n";
import { Link } from "react-router-dom";

export function TodayPage() {
  const [day, setDay] = useState(isoDay(new Date()));
  const [err, setErr] = useState<string | null>(null);
  const menu = useMenu(day);
  const needs = useNeeds();
  const dishName = useDishNames();
  const md = menu.data?.[0] ?? null;
  const { t, fmtDate } = useI18n();

  const onError = (x: unknown) => setErr(errorMessage(x, t));
  const gen = useMenuMutation(() => generateDay(day));
  const adjust = useMenuMutation((v: { slot: string; food_code: string; delta_g: number }) =>
    post(`/menu/${day}/adjust`, v));
  const unlock = useMenuMutation((v: { slot: string; food_code: string }) => post(`/menu/${day}/unlock`, v));
  const recipe = useMenuMutation((slot: string) => post(`/menu/${day}/meals/${slot}/recipe`));
  const busy = gen.isPending || adjust.isPending || unlock.isPending || recipe.isPending;
  const run = <V,>(m: { mutate: (v: V, o: { onError: (e: unknown) => void; onSuccess: () => void }) => void }, v: V) => {
    setErr(null);
    m.mutate(v, { onError, onSuccess: () => setErr(null) });
  };

  const blocked = needs.data?.expert_confirmation_required ?? [];

  return (
    <main>
      <div className="daynav">
        <button className="secondary" onClick={() => setDay(addDays(day, -1))} aria-label={t.today.prevDay}>‹</button>
        <h2>{day === isoDay(new Date()) ? t.today.today : fmtDate(day)}</h2>
        <button className="secondary" onClick={() => setDay(addDays(day, 1))} aria-label={t.today.nextDay}>›</button>
      </div>
      <Notices notices={md?.notices ?? needs.data?.notices ?? []} />
      {blocked.length > 0 && (
        <p className="notice notice-warn">
          {t.today.expertRequired} <Link to="/settings">{t.today.expertLink}</Link>
        </p>
      )}
      {err && <p className="error">{err}</p>}
      {md?.energy_adjustment_kcal ? (
        <p className="notice">
          {fmt(t.today.energyAdjusted, { kcal: Math.round(md.energy_adjustment_kcal / 10) * 10 })}
        </p>
      ) : null}
      {!md && !menu.isLoading && (
        <div className="card center">
          <p>{t.today.empty}</p>
          <button disabled={busy || blocked.length > 0} onClick={() => run(gen, undefined)}>{t.today.generate}</button>
        </div>
      )}
      {md && (
        <>
          <DaySummary plan={md.plan} />
          {md.plan.meals.map((m) => (
            <MealCard key={m.slot} meal={m} dishName={dishName(m.dish_code)} recipe={md.recipes[m.slot]} busy={busy}
                      onAdjust={(food, delta) => run(adjust, { slot: m.slot, food_code: food, delta_g: delta })}
                      onUnlock={(food) => run(unlock, { slot: m.slot, food_code: food })}
                      onRecipe={() => run(recipe, m.slot)} />
          ))}
          <button className="secondary" disabled={busy} onClick={() => run(gen, undefined)}>{t.today.regenerate}</button>
        </>
      )}
    </main>
  );
}
