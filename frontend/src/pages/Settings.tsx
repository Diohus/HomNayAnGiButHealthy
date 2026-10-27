import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { del, post, setTokens } from "../api/client";
import { useNeeds } from "../api/hooks";
import { LanguagePicker, ThemePicker } from "../components/Choice";
import { errorMessage, useI18n } from "../i18n";

const LIMITS = ["energy_kcal_max", "protein_g_max", "sodium_mg_max", "potassium_mg_max", "phosphorus_mg_max"] as const;

function ExpertForm({ condition }: { condition: string }) {
  const [vals, setVals] = useState<Record<string, string>>({});
  const [consulted, setConsulted] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const qc = useQueryClient();
  const { t } = useI18n();
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const limits = Object.fromEntries(Object.entries(vals).filter(([, v]) => v !== "").map(([k, v]) => [k, Number(v)]));
    try {
      await post("/expert-confirmations", { condition, confirmed_consulted_expert: consulted, limits });
      qc.invalidateQueries();
    } catch (x) {
      setErr(errorMessage(x, t));
    }
  }
  return (
    <form className="card form" onSubmit={submit}>
      <strong>{t.profile.conditionNames[condition]}</strong>
      <p className="small muted">{t.settings.expertHelp}</p>
      {LIMITS.map((k) => (
        <label key={k}>{t.settings.limits[k]}<input type="number" step="any" value={vals[k] ?? ""}
                                     onChange={(e) => setVals({ ...vals, [k]: e.target.value })} /></label>
      ))}
      <label className="check">
        <input type="checkbox" checked={consulted} onChange={(e) => setConsulted(e.target.checked)} />
        {t.settings.expertConfirm}
      </label>
      {err && <p className="error">{err}</p>}
      <button type="submit" disabled={!consulted}>{t.settings.confirm}</button>
    </form>
  );
}

export function SettingsPage() {
  const needs = useNeeds();
  const nav = useNavigate();
  const qc = useQueryClient();
  const { t } = useI18n();
  async function deleteAll() {
    if (!window.confirm(t.settings.deleteConfirm)) return;
    await del("/me");
    setTokens(null, null);
    qc.clear();
    nav("/login");
  }
  return (
    <main>
      {(needs.data?.expert_confirmation_required ?? []).length > 0 && (
        <>
          <h2>{t.settings.expertTitle}</h2>
          {needs.data!.expert_confirmation_required.map((c) => <ExpertForm key={c} condition={c} />)}
        </>
      )}
      <h2>{t.nav.settings}</h2>
      <div className="card">
        <ThemePicker />
        <LanguagePicker />
      </div>
      <h2>{t.settings.dataTitle}</h2>
      <div className="card">
        <button className="danger" onClick={deleteAll}>{t.settings.deleteAll}</button>
        <button className="link" onClick={() => { setTokens(null, null); qc.clear(); nav("/login"); }}>{t.logout}</button>
      </div>
    </main>
  );
}
