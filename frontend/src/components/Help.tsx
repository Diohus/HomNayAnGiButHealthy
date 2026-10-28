import { useState } from "react";
import { Link } from "react-router-dom";
import { dismissHelpBanner, shouldShowHelpBanner } from "../help";
import { useI18n } from "../i18n";

/** Link nhỏ "Xem hướng dẫn" (hoặc "?" khi chật chỗ) tới một mục của trang /help (vòng 11, G2.4). */
export function HelpLink({ section, compact = false }: { section: string; compact?: boolean }) {
  const { t } = useI18n();
  return (
    <Link className={compact ? "help-q" : "small help-link"} to={`/help#${section}`}
          aria-label={compact ? t.help.more : undefined} title={compact ? t.help.more : undefined}>
      {compact ? "?" : t.help.more}
    </Link>
  );
}

/** Banner "Mới dùng?" ở Hôm nay cho tới khi người dùng bấm ✕ (lưu hnag_help_seen; storage lỗi ⇒ chỉ ẩn trong phiên). */
export function HelpBanner() {
  const { t } = useI18n();
  const [show, setShow] = useState(shouldShowHelpBanner);
  if (!show) return null;
  return (
    <p className="notice help-banner">
      <Link to="/help">{t.help.banner}</Link>
      <button type="button" className="chip-x" aria-label={t.help.bannerClose} title={t.help.bannerClose}
              onClick={() => { dismissHelpBanner(); setShow(false); }}>✕</button>
    </p>
  );
}
