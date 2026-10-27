import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { post, setTokens } from "../api/client";
import { LanguagePicker } from "../components/Choice";
import { errorMessage, useI18n } from "../i18n";

export function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const nav = useNavigate();
  const { t } = useI18n();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      const r = await post<{ access_token: string; refresh_token: string }>(`/auth/${mode}`, { email, password });
      setTokens(r.access_token, r.refresh_token);
      nav(mode === "register" ? "/onboarding" : "/");
    } catch (x) {
      setErr(errorMessage(x, t));
    }
  }

  return (
    <main className="auth">
      <h1>{t.appName}</h1>
      <form className="card" onSubmit={submit}>
        <label>{t.email}<input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>{t.password}
          <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        {err && <p className="error">{err}</p>}
        <button type="submit">{mode === "login" ? t.login : t.register}</button>
        <button type="button" className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? t.noAccount : t.haveAccount}
        </button>
      </form>
      <div className="card lang"><LanguagePicker /></div>
    </main>
  );
}
