import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, post } from "../api/client";
import { useFoodNames } from "../api/hooks";
import { fmtKcal } from "../format";
import { errorMessage, fmt, useI18n } from "../i18n";
import type { ChatReply, ClarifyItem, Proposal } from "../types";

interface Msg {
  role: "user" | "assistant"; text: string; kind?: string; proposals?: Proposal[]; unknown?: string[];
  clarify?: ClarifyItem[]; source?: string; // source: original message, resent with the user's choice
}

function LabelForm({ name, onDone }: { name: string; onDone: (msg: string) => void }) {
  const [f, setF] = useState({ name_vi: name, energy_kcal: "", protein_g: "", carb_g: "", fat_g: "", portion_g: "" });
  const [allergens, setAllergens] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const { t } = useI18n();
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await post("/foods/custom", {
        name_vi: f.name_vi, portion_g: Number(f.portion_g), contains_allergens: allergens,
        per_100g: { energy_kcal: Number(f.energy_kcal), protein_g: Number(f.protein_g), carb_g: Number(f.carb_g),
                    fat_g: Number(f.fat_g) },
      });
      onDone(fmt(t.chat.label.saved, { name: f.name_vi, source: t.userProvided }));
    } catch (x) {
      setErr(errorMessage(x, t));
    }
  }
  return (
    <form className="card form" onSubmit={submit}>
      <strong>{t.chat.labelTitle}</strong>
      <label>{t.chat.label.name}<input value={f.name_vi} onChange={set("name_vi")} required /></label>
      <div className="grid3">
        <label>{t.chat.label.kcal}<input type="number" step="any" value={f.energy_kcal} onChange={set("energy_kcal")} required /></label>
        <label>{t.chat.label.protein}<input type="number" step="any" value={f.protein_g} onChange={set("protein_g")} required /></label>
        <label>{t.chat.label.carb}<input type="number" step="any" value={f.carb_g} onChange={set("carb_g")} required /></label>
        <label>{t.chat.label.fat}<input type="number" step="any" value={f.fat_g} onChange={set("fat_g")} required /></label>
        <label>{t.chat.label.portion}<input type="number" step="any" value={f.portion_g} onChange={set("portion_g")} required /></label>
      </div>
      <fieldset><legend>{t.chat.label.contains}</legend>
        <div className="chips">
          {Object.entries(t.profile.allergenNames).map(([k, v]) => (
            <label key={k} className={`chip ${allergens.includes(k) ? "on" : ""}`}>
              <input type="checkbox" checked={allergens.includes(k)}
                     onChange={() => setAllergens(allergens.includes(k) ? allergens.filter((x) => x !== k) : [...allergens, k])} />
              {v}
            </label>
          ))}
        </div>
      </fieldset>
      {err && <p className="error">{err}</p>}
      <button type="submit">{t.chat.label.save}</button>
    </form>
  );
}

function ProposalCard({ p, onApplied }: { p: Proposal; onApplied: (m: string) => void }) {
  const name = useFoodNames();
  const [state, setState] = useState<"idle" | "busy" | "done">("idle");
  const [err, setErr] = useState<string | null>(null);
  const qc = useQueryClient();
  const { t } = useI18n();
  async function apply() {
    setState("busy");
    try {
      await post(`/chat/proposals/${p.id}/apply`);
      setState("done");
      await qc.invalidateQueries({ queryKey: [p.preference ? "dislikes" : "menu"] });
      if (p.key === "log" || p.key === "rebalance") await qc.invalidateQueries({ queryKey: ["shopping"] });
      onApplied(p.preference ? t.chat.dislikeSaved : t.chat.applied);
    } catch (x) {
      setErr(errorMessage(x, t));
      setState("idle");
    }
  }
  return (
    <div className="proposal">
      <p><strong>{p.label}</strong></p>
      {p.plan && (
        <details>
          <summary className="small">{fmt(t.chat.details, { kcal: fmtKcal(p.plan.totals.energy_kcal ?? 0) })}</summary>
          {p.plan.meals.map((m) => (
            <p key={m.slot} className="small">
              {t.slots[m.slot]}: {m.items.map((i) => `${Math.round(i.grams)} g ${name(i.food_code).toLowerCase()}`).join(", ")}
            </p>
          ))}
        </details>
      )}
      {err && <p className="error">{err}</p>}
      <button disabled={state !== "idle"} onClick={apply}>{state === "done" ? "✓" : t.chat.apply}</button>
    </div>
  );
}

export function ChatPage() {
  const history = useQuery({
    queryKey: ["chat-history"],
    queryFn: () => api<{ role: "user" | "assistant"; text: string; kind?: string }[]>("/chat/history"),
  });
  const [extra, setExtra] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const { t } = useI18n();
  const msgs: Msg[] = [...(history.data ?? []), ...extra];

  async function ask(m: string, resolved?: Record<string, string>) {
    setBusy(true);
    try {
      const r = await post<ChatReply>("/chat", { message: m, ...(resolved ? { resolved } : {}) });
      setExtra((x) => [...x, { role: "assistant", text: r.text, kind: r.kind, proposals: r.proposals,
                               unknown: r.kind === "need_label" ? r.unknown_mentions : undefined,
                               clarify: r.kind === "clarify" ? r.clarify : undefined, source: m }]);
    } catch (x) {
      setExtra((xs) => [...xs, { role: "assistant", text: errorMessage(x, t), kind: "error" }]);
    } finally {
      setBusy(false);
    }
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    const m = text;
    setText("");
    setExtra((x) => [...x, { role: "user", text: m }]);
    await ask(m);
  }

  // Clarify: the user picks one option per mention, then the original message is resent with the choices.
  function pick(m: Msg, mention: string, code: string, name: string) {
    setExtra((x) => [...x, { role: "user", text: `${mention} → ${name}` }]);
    void ask(m.source ?? "", { [mention]: code });
  }

  return (
    <main className="chat">
      <div className="messages">
        {msgs.map((m, i) => (
          <div key={i} className={`bubble ${m.role} ${m.kind ?? ""}`}>
            {m.text.split("\n").map((l, j) => <p key={j}>{l}</p>)}
            {m.proposals?.map((p) => (
              <ProposalCard key={p.id} p={p} onApplied={(s) => setExtra((x) => [...x, { role: "assistant", text: s }])} />
            ))}
            {m.clarify?.map((c) => (
              <div key={c.mention} className="clarify" role="group" aria-label={fmt(t.chat.clarifyFor, { mention: c.mention })}>
                <p className="small">“{c.mention}”</p>
                {c.options.map((o) => (
                  <button key={o.code} type="button" className="secondary" disabled={busy}
                          onClick={() => pick(m, c.mention, o.code, o.name)}>{o.name}</button>
                ))}
              </div>
            ))}
            {m.kind === "allergy_redirect" && <Link to="/profile">{t.chat.openProfile}</Link>}
            {m.unknown !== undefined && (
              <LabelForm name={m.unknown[0] ?? ""} onDone={(s) => setExtra((x) => [...x, { role: "assistant", text: s }])} />
            )}
          </div>
        ))}
        {busy && <div className="bubble assistant muted">…</div>}
      </div>
      <form className="composer" onSubmit={send}>
        <input aria-label={t.chat.message} value={text} maxLength={1000} placeholder={t.chat.placeholder} onChange={(e) => setText(e.target.value)} />
        <button type="submit" disabled={busy}>{t.chat.send}</button>
      </form>
    </main>
  );
}
