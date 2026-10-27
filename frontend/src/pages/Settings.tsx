import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { del, setTokens } from "../api/client";
import { LanguagePicker, ThemePicker } from "../components/Choice";
import { HealthLimitsSection } from "../components/HealthLimits";
import { useI18n } from "../i18n";

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
        <button className="danger" onClick={deleteAll}>{t.settings.deleteAll}</button>
        <button className="link" onClick={() => { setTokens(null, null); qc.clear(); nav("/login"); }}>{t.logout}</button>
      </div>
    </main>
  );
}
