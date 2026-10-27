import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, put } from "../api/client";
import { useNeeds, useProfile } from "../api/hooks";
import { Notices } from "../components/Notices";
import { fmtKcal, fmtSig } from "../format";
import { errorMessage, fmt, useI18n } from "../i18n";
import type { Profile } from "../types";

const EMPTY: Profile = {
  sex: "female", age: 30, height_cm: 160, weight_kg: 55, activity_level: "moderate", goal: "maintain",
  conditions: [], uses_insulin_or_glucose_meds: false, allergies: [], diets: [], custom_target_kcal: null,
  acknowledge_low_energy: false,
};

function toggle(list: string[], v: string) {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
}

export function ProfilePage({ onboarding = false }: { onboarding?: boolean }) {
  const { data } = useProfile();
  const [p, setP] = useState<Profile>(EMPTY);
  const [accepted, setAccepted] = useState(!onboarding);
  const [err, setErr] = useState<string | null>(null);
  const [needAck, setNeedAck] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const qc = useQueryClient();
  const nav = useNavigate();
  const needs = useNeeds(!!data?.profile);
  const { t } = useI18n();

  useEffect(() => {
    if (data?.profile) setP({ ...EMPTY, ...data.profile });
  }, [data]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    try {
      await put("/profile", p);
      await qc.invalidateQueries();
      setMsg(t.profile.saved);
      if (onboarding) nav("/");
    } catch (x) {
      if (x instanceof ApiError && x.code === "LOW_ENERGY_ACK_REQUIRED") setNeedAck(true);
      setErr(errorMessage(x, t));
    }
  }

  const num = (k: keyof Profile) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setP({ ...p, [k]: e.target.value === "" ? null : Number(e.target.value) });

  return (
    <main>
      <h2>{t.profile.title}</h2>
      {onboarding && (
        <div className="card">
          <Notices notices={[{ code: "DISCLAIMER", text: t.notices.DISCLAIMER }]} />
          <label className="check">
            <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} /> {t.disclaimerAccept}
          </label>
        </div>
      )}
      <form className="card form" onSubmit={save}>
        <fieldset>
          <legend>{t.profile.sex}</legend>
          {["female", "male"].map((s) => (
            <label key={s} className="check">
              <input type="radio" name="sex" checked={p.sex === s} onChange={() => setP({ ...p, sex: s })} />
              {s === "male" ? t.profile.male : t.profile.female}
            </label>
          ))}
        </fieldset>
        <div className="grid3">
          <label>{t.profile.age}<input type="number" step="1" value={p.age ?? ""} onChange={num("age")} required /></label>
          <label>{t.profile.height}<input type="number" step="0.1" value={p.height_cm ?? ""} onChange={num("height_cm")} required /></label>
          <label>{t.profile.weight}<input type="number" step="0.1" value={p.weight_kg ?? ""} onChange={num("weight_kg")} required /></label>
        </div>
        <label>{t.profile.activity}
          <select value={p.activity_level} onChange={(e) => setP({ ...p, activity_level: e.target.value })}>
            {Object.entries(t.profile.activities).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label>{t.profile.goal}
          <select value={p.goal} onChange={(e) => setP({ ...p, goal: e.target.value })}>
            {Object.entries(t.profile.goals).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        {([["conditions", t.profile.conditions, t.profile.conditionNames],
           ["allergies", t.profile.allergies, t.profile.allergenNames],
           ["diets", t.profile.diets, t.profile.dietNames]] as const).map(([key, label, names]) => (
          <fieldset key={key}>
            <legend>{label}</legend>
            <div className="chips">
              {Object.entries(names).map(([k, v]) => (
                <label key={k} className={`chip ${(p[key] as string[]).includes(k) ? "on" : ""}`}>
                  <input type="checkbox" checked={(p[key] as string[]).includes(k)}
                         onChange={() => setP({ ...p, [key]: toggle(p[key] as string[], k) })} />
                  {v}
                </label>
              ))}
            </div>
          </fieldset>
        ))}
        {p.conditions.some((c) => c.startsWith("diabetes")) && (
          <label className="check">
            <input type="checkbox" checked={p.uses_insulin_or_glucose_meds}
                   onChange={(e) => setP({ ...p, uses_insulin_or_glucose_meds: e.target.checked })} />
            {t.profile.meds}
          </label>
        )}
        <label>{t.profile.customKcal}
          <input type="number" step="1" value={p.custom_target_kcal ?? ""} onChange={num("custom_target_kcal")} />
        </label>
        {needAck && (
          <label className="check warn">
            <input type="checkbox" checked={p.acknowledge_low_energy}
                   onChange={(e) => setP({ ...p, acknowledge_low_energy: e.target.checked })} />
            {t.profile.lowEnergyAck}
          </label>
        )}
        {err && <p className="error">{err}</p>}
        {msg && <p className="ok">{msg}</p>}
        <button type="submit" disabled={!accepted}>{t.profile.save}</button>
      </form>

      {needs.data && (
        <section className="card">
          <h3>{t.needs.title}</h3>
          <p className="small muted">
            {t.needs.bmr} {fmtKcal(needs.data.needs.bmr_kcal)} kcal {"\u00d7"} {needs.data.needs.activity_factor} = {t.needs.tdee}{" "}
            {fmtKcal(needs.data.needs.tdee_kcal)} kcal · {fmt(t.needs.mealsPerDay, { n: needs.data.needs.meals_per_day })}
          </p>
          <table className="needs">
            <tbody>
              {needs.data.needs.targets.map((tg) => (
                <tr key={tg.code}>
                  <td>{t.macros[tg.code] ?? tg.code}</td>
                  <td>{tg.kind === "max" ? "≤ " : tg.kind === "min" ? "≥ " : ""}
                    {tg.unit === "kcal" ? fmtKcal(tg.value) : fmtSig(tg.value)} {tg.unit}</td>
                  <td className="small muted">
                    {tg.reference.source}{tg.reference.applies_to ? ` · ${tg.reference.applies_to}` : ""}
                    {tg.reference.note ? ` · ${tg.reference.note}` : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {needs.data.needs.assumptions.map((a) => <p key={a} className="small muted">{fmt(t.needs.assumption, { text: a })}</p>)}
        </section>
      )}
    </main>
  );
}
