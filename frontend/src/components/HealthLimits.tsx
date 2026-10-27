import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { del, postForm, put } from "../api/client";
import { useHealthLimits } from "../api/hooks";
import { errorMessage, fmt, useI18n } from "../i18n";
import { LIMIT_FIELDS, type ExtractDraft, type HealthLimitRow, type LimitField } from "../types";

type Mode = "manual" | "image" | "text";
type Vals = Partial<Record<LimitField, string>>;
interface Editing { condition: string | null; vals: Vals; source: "manual" | "document" }

const toVals = (limits: Partial<Record<LimitField, number | null>>): Vals =>
  Object.fromEntries(Object.entries(limits).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)]));

// User-provided health limits: list, add/edit by hand, or extract from a photo/text with AI (draft only).
export function HealthLimitsSection() {
  const { t } = useI18n();
  const list = useHealthLimits();
  const qc = useQueryClient();
  const [editing, setEditing] = useState<Editing | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const { hash } = useLocation();
  // Link "/settings#health-limits" from Profile: the router does not scroll to hashes by itself
  useEffect(() => {
    if (hash === "#health-limits" && list.data) document.getElementById("health-limits")?.scrollIntoView();
  }, [hash, list.data]);

  const refresh = () => Promise.all(["health-limits", "needs", "menu"].map((k) => qc.invalidateQueries({ queryKey: [k] })));
  async function remove(row: HealthLimitRow) {
    if (!window.confirm(t.limits.deleteConfirm)) return;
    try {
      await del(`/health-limits/${row.id}`);
      await refresh();
    } catch (x) {
      setErr(errorMessage(x, t));
    }
  }

  return (
    <section id="health-limits">
      <h2>{t.limits.title}</h2>
      <p className="small muted">{t.limits.help}</p>
      {(list.data ?? []).map((row) => (
        <LimitRow key={row.id} row={row} onEdit={() => setEditing({ condition: row.condition, source: row.source,
                                                                     vals: toVals(row.limits) })}
                  onDelete={() => remove(row)} />
      ))}
      {list.data?.length === 0 && !editing && <p className="card small muted">{t.limits.empty}</p>}
      {err && <p className="error">{err}</p>}
      {editing ? (
        <LimitEditor initial={editing} onDone={async () => { setEditing(null); await refresh(); }}
                     onCancel={() => setEditing(null)} />
      ) : (
        <button className="secondary" onClick={() => setEditing({ condition: null, vals: {}, source: "manual" })}>
          {t.limits.add}
        </button>
      )}
    </section>
  );
}

function LimitRow({ row, onEdit, onDelete }: { row: HealthLimitRow; onEdit: () => void; onDelete: () => void }) {
  const { t, fmtDate } = useI18n();
  const values = LIMIT_FIELDS.filter((k) => row.limits[k] != null);
  return (
    <div className="card">
      <strong>{row.condition ? t.profile.conditionNames[row.condition] : t.limits.general}</strong>
      <p className="small muted">
        {t.limits.sources[row.source]} · {fmtDate(row.confirmed_at.slice(0, 10))}
      </p>
      <ul className="small">
        {values.map((k) => <li key={k}>{t.settings.limits[k]}: {row.limits[k]}</li>)}
      </ul>
      <button className="link" onClick={onEdit}>{t.limits.edit}</button>
      <button className="link" onClick={onDelete}>{t.limits.remove}</button>
    </div>
  );
}

function LimitEditor({ initial, onDone, onCancel }: { initial: Editing; onDone: () => void; onCancel: () => void }) {
  const { t } = useI18n();
  const [mode, setMode] = useState<Mode>("manual");
  const [condition, setCondition] = useState<string | null>(initial.condition);
  const [vals, setVals] = useState<Vals>(initial.vals);
  const [source, setSource] = useState(initial.source);
  const [draft, setDraft] = useState<ExtractDraft | null>(null);
  const [consent, setConsent] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function read() {
    setErr(null);
    setBusy(true);
    const form = new FormData();
    form.append("consent_ai_processing", String(consent));
    if (mode === "image" && file) form.append("file", file);
    if (mode === "text") form.append("text", text);
    try {
      const d = await postForm<ExtractDraft>("/health-limits/extract", form);
      setDraft(d);
      setVals(toVals(d.limits));
      setSource("document");
    } catch (x) {
      setErr(errorMessage(x, t));
    } finally {
      setBusy(false);
    }
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    const limits = Object.fromEntries(Object.entries(vals).filter(([, v]) => v !== "").map(([k, v]) => [k, Number(v)]));
    try {
      await put("/health-limits", { condition, limits, source });
      onDone();
    } catch (x) {
      setErr(errorMessage(x, t));
    }
  }

  const quote = (k: LimitField) => draft?.items.find((i) => i.field === k);
  const showForm = mode === "manual" || draft !== null;

  return (
    <div className="card form">
      <div className="seg" role="tablist" aria-label={t.limits.add}>
        {(["manual", "image", "text"] as const).map((m) => (
          <button key={m} type="button" role="tab" aria-selected={mode === m}
                  className={mode === m ? "" : "secondary"} onClick={() => { setMode(m); setErr(null); }}>
            {t.limits.tabs[m]}
          </button>
        ))}
      </div>

      {mode !== "manual" && (
        <div className="extract">
          {mode === "image" ? (
            <label>{t.limits.imageLabel}
              <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment"
                     onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </label>
          ) : (
            <label>{t.limits.textLabel}
              <textarea rows={6} maxLength={5000} value={text} onChange={(e) => setText(e.target.value)} />
            </label>
          )}
          <label className="check">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            {t.limits.consent}
          </label>
          <button type="button" disabled={busy || !consent || (mode === "image" ? !file : !text.trim())}
                  onClick={read} aria-busy={busy}>
            {busy ? t.limits.reading : t.limits.read}
          </button>
          {draft && <p className="notice notice-warn">{t.limits.reviewHint}</p>}
        </div>
      )}

      {showForm && (
        <form onSubmit={save}>
          <label>{t.limits.condition}
            <select value={condition ?? ""} onChange={(e) => setCondition(e.target.value || null)}>
              <option value="">{t.limits.general}</option>
              {Object.entries(t.profile.conditionNames).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          {LIMIT_FIELDS.map((k) => {
            const q = quote(k);
            return (
              <label key={k}>{t.settings.limits[k]}
                <input type="number" step="any" min="0" value={vals[k] ?? ""}
                       onChange={(e) => setVals({ ...vals, [k]: e.target.value })} />
                {q && (
                  <span className="small muted quote">
                    “{q.quote}”{q.converted_from === "salt"
                      ? ` ${fmt(t.limits.convertedSalt, { value: q.original_value })}`
                      : q.original_unit !== q.unit
                        ? ` ${fmt(t.limits.converted, { value: q.original_value, unit: q.original_unit })}` : ""}
                  </span>
                )}
              </label>
            );
          })}
          {draft && draft.rejected.length > 0 && (
            <div className="small">
              <strong>{t.limits.rejected}</strong>
              <ul>
                {draft.rejected.map((r, i) => (
                  <li key={i}>{t.settings.limits[r.field]}: {r.value} {r.unit} — “{r.quote}” ({r.reason_text})</li>
                ))}
              </ul>
            </div>
          )}
          {draft && draft.other_instructions.length > 0 && (
            <div className="small">
              <strong>{t.limits.others}</strong>
              <ul>{draft.other_instructions.map((o, i) => <li key={i}>{o}</li>)}</ul>
            </div>
          )}
          {err && <p className="error">{err}</p>}
          <button type="submit">{t.limits.save}</button>
          <button type="button" className="link" onClick={onCancel}>{t.limits.cancel}</button>
        </form>
      )}
      {!showForm && err && <p className="error">{err}</p>}
      {!showForm && <button type="button" className="link" onClick={onCancel}>{t.limits.cancel}</button>}
    </div>
  );
}
