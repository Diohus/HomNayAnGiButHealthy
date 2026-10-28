import { useState } from "react";
import { post, postForm } from "../api/client";
import { errorMessage, fmt, useI18n } from "../i18n";
import type { PhotoDraft } from "../types";

const SLOTS = ["breakfast", "lunch", "dinner", "snack"];

// Meal photo ⇒ editable draft (AI estimate, nothing saved) ⇒ "Log" writes all rows at once (/intake/batch).
export function PhotoIntake({ day, onSaved }: { day: string; onSaved: () => void }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [draft, setDraft] = useState<PhotoDraft | null>(null);
  const [slot, setSlot] = useState("lunch");

  function reset() {
    setOpen(false); setFile(null); setDraft(null); setErr(null);
  }

  async function analyze() {
    if (!file) return;
    setBusy(true); setErr(null);
    const form = new FormData();
    form.append("file", file);
    form.append("day", day);
    form.append("consent_ai_processing", String(consent));
    try {
      const d = await postForm<PhotoDraft>("/intake/photo", form);
      setDraft(d);
      setSlot(d.slot);
    } catch (x) {
      setErr(errorMessage(x, t));
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!draft) return;
    setBusy(true); setErr(null);
    try {
      await post("/intake/batch", { day, entries: draft.entries.map((e) => (
        { slot, food_code: e.food_code, grams: e.grams, source: "ai_estimate" })) });
      reset();
      onSaved();
    } catch (x) {
      setErr(errorMessage(x, t));
    } finally {
      setBusy(false);
    }
  }

  const setGrams = (i: number, g: number) => draft && setDraft({
    ...draft, entries: draft.entries.map((e, j) => (j === i ? { ...e, grams: g } : e)) });
  const drop = (i: number) => draft && setDraft({ ...draft, entries: draft.entries.filter((_, j) => j !== i) });

  if (!open) return <button className="secondary" onClick={() => setOpen(true)}>{t.intake.photo.open}</button>;

  return (
    <div className="form">
      {!draft ? (
        <>
          <label>{t.intake.photo.file}
            <input type="file" accept="image/jpeg,image/png,image/webp" capture="environment"
                   onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          </label>
          <label className="check">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            {t.intake.photo.consent}
          </label>
          <button type="button" disabled={busy || !file || !consent} onClick={analyze}>
            {busy ? t.intake.photo.analyzing : t.intake.photo.analyze}
          </button>
        </>
      ) : (
        <>
          <p><strong>{t.intake.photo.draft}</strong> <span className="tag">{t.today.tags.aiEstimate}</span></p>
          {draft.entries.length === 0 && <p className="small muted">{t.intake.photo.empty}</p>}
          <ul className="items">
            {draft.entries.map((e, i) => (
              <li key={`${e.food_code}-${i}`}>
                <span>{e.name} <span className="small muted">· {e.seen_as}</span></span>
                <span className="item-ctl">
                  <input type="number" min="1" max="3000" value={e.grams} aria-label={fmt(t.intake.photo.gramsFor, { name: e.name })}
                         onChange={(x) => setGrams(i, Number(x.target.value))} /> g
                  <button type="button" className="link" onClick={() => drop(i)}>{t.pantry.remove}</button>
                </span>
              </li>
            ))}
          </ul>
          {draft.unresolved.length > 0 && (
            <p className="small muted">{fmt(t.intake.photo.unresolved, { names: draft.unresolved.join(", ") })}</p>
          )}
          {draft.rejected.map((r, i) => (
            <p key={i} className="small error">{fmt(t.intake.photo.rejected, { food: r.food, reason: r.reason })}</p>
          ))}
          <label>{t.intake.meal}
            <select value={slot} onChange={(e) => setSlot(e.target.value)}>
              {SLOTS.map((s) => <option key={s} value={s}>{t.slots[s]}</option>)}
            </select>
          </label>
          <button type="button" disabled={busy || draft.entries.length === 0
                                          || draft.entries.some((e) => !(e.grams >= 1 && e.grams <= 3000))}
                  onClick={save}>{t.intake.add}</button>
        </>
      )}
      {err && <p className="error">{err}</p>}
      <button type="button" className="link" onClick={reset}>{t.limits.cancel}</button>
    </div>
  );
}
