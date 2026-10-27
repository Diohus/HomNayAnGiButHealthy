import { QueryClient, QueryClientProvider, useQueryClient } from "@tanstack/react-query";
import React, { useEffect, useRef } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { hasSession } from "./api/client";
import { useProfile } from "./api/hooks";
import { I18nProvider, useI18n } from "./i18n";
import { AuthPage } from "./pages/Auth";
import { ChatPage } from "./pages/Chat";
import { PantryPage } from "./pages/Pantry";
import { ProfilePage } from "./pages/Profile";
import { SettingsPage } from "./pages/Settings";
import { ShoppingPage } from "./pages/Shopping";
import { TodayPage } from "./pages/Today";
import { applyTheme, getTheme } from "./theme";
import "./styles.css";

applyTheme(getTheme()); // theme-init.js already set data-theme; resync meta theme-color

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } });

// E9: language change ⇒ refetch all server data (needs, notices, menus, dish names) in the new language
function LangSync() {
  const { lang } = useI18n();
  const qc = useQueryClient();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    qc.invalidateQueries();
  }, [lang, qc]);
  return null;
}

function Shell({ children }: { children: React.ReactNode }) {
  const profile = useProfile();
  const loc = useLocation();
  const { t } = useI18n();
  if (!hasSession()) return <Navigate to="/login" />;
  if (profile.data && !profile.data.profile && loc.pathname !== "/onboarding") return <Navigate to="/onboarding" />;
  return (
    <div className="shell">
      {children}
      <nav className="tabs">
        <NavLink to="/" end>{t.nav.today}</NavLink>
        <NavLink to="/chat">{t.nav.chat}</NavLink>
        <NavLink to="/pantry">{t.nav.pantry}</NavLink>
        <NavLink to="/shopping">{t.nav.shopping}</NavLink>
        <NavLink to="/profile">{t.nav.profile}</NavLink>
        <NavLink to="/settings" aria-label={t.nav.settings} title={t.nav.settings}>⚙</NavLink>
      </nav>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <I18nProvider>
    <QueryClientProvider client={qc}>
      <LangSync />
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<AuthPage />} />
          <Route path="/onboarding" element={<Shell><ProfilePage onboarding /></Shell>} />
          <Route path="/" element={<Shell><TodayPage /></Shell>} />
          <Route path="/chat" element={<Shell><ChatPage /></Shell>} />
          <Route path="/pantry" element={<Shell><PantryPage /></Shell>} />
          <Route path="/shopping" element={<Shell><ShoppingPage /></Shell>} />
          <Route path="/profile" element={<Shell><ProfilePage /></Shell>} />
          <Route path="/settings" element={<Shell><SettingsPage /></Shell>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
    </I18nProvider>
  </React.StrictMode>,
);
