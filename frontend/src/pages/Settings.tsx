import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { del, post, setTokens } from "../api/client";
import { LanguagePicker, ThemePicker } from "../components/Choice";
import { HealthLimitsSection } from "../components/HealthLimits";
import { isoDay } from "../format";
import { errorMessage, useI18n } from "../i18n";

// P2: re-enter password ⇒ POST /me/export ⇒ save as a JSON file (nothing is kept in the page afterwards).
function ExportData() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setMsg(null);
    try {
      const data = await post<unknown>("/me/export", { password: pw });
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `homnayangi-data-${isoDay(new Date())}.json`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setPw(""); setOpen(false);
      setMsg({ ok: true, text: t.settings.exportDone });
    } catch (x) {
      setMsg({ ok: false, text: errorMessage(x, t) });
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      {open ? (
        <form className="form" onSubmit={submit}>
          <p className="small muted">{t.settings.exportHint}</p>
          <label>{t.settings.password}
            <input type="password" autoComplete="current-password" value={pw} onChange={(e) => setPw(e.target.value)} required />
          </label>
          <button type="submit" disabled={busy || !pw}>{t.settings.exportDo}</button>
          <button type="button" className="link" onClick={() => { setOpen(false); setPw(""); }}>{t.limits.cancel}</button>
        </form>
      ) : (
        <button className="secondary" onClick={() => { setOpen(true); setMsg(null); }}>{t.settings.export}</button>
      )}
      {msg && <p className={msg.ok ? "ok small" : "error small"}>{msg.text}</p>}
    </>
  );
}

export function SettingsPage() {
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
      <HealthLimitsSection />
      <h2>{t.nav.settings}</h2>
      <div className="card">
        <ThemePicker />
        <LanguagePicker />
      </div>
      <h2>{t.settings.dataTitle}</h2>
      <div className="card">
        <ExportData />
      </div>
      <div className="card">
        <button className="danger" onClick={deleteAll}>{t.settings.deleteAll}</button>
        <button className="link" onClick={() => { setTokens(null, null); qc.clear(); nav("/login"); }}>{t.logout}</button>
      </div>
    </main>
  );
}
