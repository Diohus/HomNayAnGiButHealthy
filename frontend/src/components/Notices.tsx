import { useI18n } from "../i18n";
import type { Notice } from "../types";

export function Notices({ notices }: { notices: Notice[] }) {
  const { t } = useI18n();
  if (!notices.length) return null;
  return (
    <div className="notices">
      {notices.map((n) => (
        <p key={n.code} className={`notice ${n.code === "DISCLAIMER" ? "" : "notice-warn"}`}>
          {t.notices[n.code] ?? n.text}
        </p>
      ))}
    </div>
  );
}
