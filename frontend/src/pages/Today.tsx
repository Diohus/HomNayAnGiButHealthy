import { useState } from "react";
import { post } from "../api/client";
import { generateDay, useDishNames, useMenu, useMenuMutation, useNeeds } from "../api/hooks";
import { DaySummary } from "../components/DaySummary";
import { HelpBanner, HelpLink } from "../components/Help";
import { IntakePanel } from "../components/IntakePanel";
import { MealCard } from "../components/MealCard";
import { Notices } from "../components/Notices";
import { addDays, isoDay } from "../format";
import { errorMessage, fmt, useI18n } from "../i18n";
import { ViewSwitch } from "./Week";

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
  const swap = useMenuMutation((slot: string) => post(`/menu/${day}/meals/${slot}/swap`));
  const eat = useMenuMutation((v: { slot: string; eaten: boolean }) =>
    post(`/menu/${day}/meals/${v.slot}/eaten`, { eaten: v.eaten }));
  const rebalance = useMenuMutation(() => post(`/menu/${day}/rebalance`));
  const busy = gen.isPending || adjust.isPending || unlock.isPending || recipe.isPending || swap.isPending
    || eat.isPending || rebalance.isPending;
  // USED_DISLIKED:<code>: a disliked dish/ingredient was used because nothing else fit
  const disliked = new Set((md?.plan.warnings ?? []).filter((w) => w.startsWith("USED_DISLIKED:")).map((w) => w.slice(14)));
  const over = (md?.plan.warnings ?? []).find((w) => w.startsWith("OVER_TARGET:"));
  const run = <V,>(m: { mutate: (v: V, o: { onError: (e: unknown) => void; onSuccess: () => void }) => void }, v: V) => {
    setErr(null);
    m.mutate(v, { onError, onSuccess: () => setErr(null) });
  };

  return (
    <main>
      <ViewSwitch />
      <HelpBanner />
      <div className="daynav">
        <button className="secondary" onClick={() => setDay(addDays(day, -1))} aria-label={t.today.prevDay}>‹</button>
        <h2>{day === isoDay(new Date()) ? t.today.today : fmtDate(day)}</h2>
        <button className="secondary" onClick={() => setDay(addDays(day, 1))} aria-label={t.today.nextDay}>›</button>
      </div>
      <Notices notices={md?.notices ?? needs.data?.notices ?? []} />
      {err && <p className="error">{err}</p>}
      {md?.energy_adjustment_kcal ? (
        <p className="notice">
          {fmt(t.today.energyAdjusted, { kcal: Math.round(md.energy_adjustment_kcal / 10) * 10 })}
        </p>
      ) : null}
      {!md && !menu.isLoading && (
        <div className="card center">
          <p>{t.today.empty} <HelpLink section="today" /></p>
          <button disabled={busy} onClick={() => run(gen, undefined)}>{t.today.generate}</button>
        </div>
      )}
      {md && (
        <>
          {over && <p className="notice notice-warn">{fmt(t.intake.over, { kcal: over.slice(12) })}</p>}
          <DaySummary plan={md.plan} eatenKcal={md.intake.totals.energy_kcal ?? 0} />
          {md.plan.meals.map((m) => (
            <MealCard key={m.slot} meal={m} dishName={dishName(m.dish_code)} recipe={md.recipes[m.slot]} busy={busy}
                      onAdjust={(food, delta) => run(adjust, { slot: m.slot, food_code: food, delta_g: delta })}
                      onUnlock={(food) => run(unlock, { slot: m.slot, food_code: food })}
                      onRecipe={() => run(recipe, m.slot)} onSwap={() => run(swap, m.slot)}
                      eaten={md.eaten_slots.includes(m.slot)}
                      onEaten={(v) => run(eat, { slot: m.slot, eaten: v })}
                      usedDisliked={(!!m.dish_code && disliked.has(m.dish_code))
                        || m.items.some((i) => disliked.has(i.food_code))} />
          ))}
          <IntakePanel md={md} day={day} busy={busy} onChanged={() => menu.refetch()}
                       onRebalance={() => run(rebalance, undefined)} />
          <button className="secondary" disabled={busy} onClick={() => run(gen, undefined)}>{t.today.regenerate}</button>
        </>
      )}
    </main>
  );
}
