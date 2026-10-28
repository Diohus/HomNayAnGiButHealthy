import { useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { hasSession } from "../api/client";
import { openSectionId, rich } from "../help";
import { useI18n } from "../i18n";

function Rich({ text }: { text: string }) {
  return <>{rich(text).map((p, i) => (p.strong ? <strong key={i}>{p.text}</strong> : <span key={i}>{p.text}</span>))}</>;
}

// Vòng 11: hướng dẫn sử dụng (nội dung: docs/USER_GUIDE.md ⇒ i18n `help`). Nằm ngoài Shell: xem được khi chưa đăng nhập.
export function HelpPage() {
  const { t } = useI18n();
  const { hash } = useLocation();
  const nav = useNavigate();
  const h = t.help;
  const open = openSectionId(hash, h.sections.map((s) => s.id));

  useEffect(() => {
    if (hash) document.getElementById(open)?.scrollIntoView({ block: "start" });
  }, [hash, open]);

  return (
    <main className="help">
      <div className="help-top">
        {hasSession()
          ? <button className="link" onClick={() => (window.history.length > 1 ? nav(-1) : nav("/"))}>{h.back}</button>
          : <Link to="/login">{h.login}</Link>}
      </div>
      <h2>{h.title}</h2>
      <section className="card">
        <h3>{h.intro.title}</h3>
        {h.intro.paragraphs.map((p, i) => <p key={i}><Rich text={p} /></p>)}
      </section>
      {h.sections.map((s) => (
        // key theo hash: đổi hash (bấm link tới mục khác) ⇒ mở lại đúng mục
        <details key={`${s.id}|${hash}`} id={s.id} className="card" open={s.id === open}>
          <summary><strong>{s.title}</strong></summary>
          {s.paragraphs.map((p, i) => <p key={i}><Rich text={p} /></p>)}
          {s.steps && <ol>{s.steps.map((p, i) => <li key={i}><Rich text={p} /></li>)}</ol>}
          {s.bullets && <ul>{s.bullets.map((p, i) => <li key={i}><Rich text={p} /></li>)}</ul>}
          {s.after?.map((p, i) => <p key={i}><Rich text={p} /></p>)}
        </details>
      ))}
    </main>
  );
}
