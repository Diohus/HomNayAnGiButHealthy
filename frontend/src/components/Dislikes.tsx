import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api, del, post } from "../api/client";
import { useDishes, useFoodNames, useFoods } from "../api/hooks";
import { errorMessage, fmt, useI18n } from "../i18n";
import { foldText as fold } from "../format";
import type { DislikeRow } from "../types";

const MAX_RESULTS = 8;

// Foods / dishes the user doesn't like: a soft constraint for the planner (allergies stay in the profile).
export function DislikesSection() {
  const { t, lang } = useI18n();
  const qc = useQueryClient();
  const list = useQuery({ queryKey: ["dislikes"], queryFn: () => api<DislikeRow[]>("/preferences/dislikes") });
  const foods = useFoods();
  const dishes = useDishes();
  const foodName = useFoodNames();
  const [q, setQ] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const taken = new Set((list.data ?? []).map((d) => `${d.kind}:${d.code}`));
  const options = useMemo(() => {
    const all = [
      ...(foods.data ?? []).map((f) => ({ kind: "food" as const, code: f.code, name: foodName(f.code) })),
      ...(dishes.data ?? []).map((d) => ({ kind: "dish" as const, code: d.code,
                                          name: lang === "en" ? d.name_en || d.name_vi : d.name_vi })),
    ];
    return all;
  }, [foods.data, dishes.data, lang, foodName]);
  const needle = fold(q.trim());
  const results = needle
    ? options.filter((o) => !taken.has(`${o.kind}:${o.code}`) && fold(o.name).includes(needle)).slice(0, MAX_RESULTS)
    : [];

  const refresh = () => qc.invalidateQueries({ queryKey: ["dislikes"] });
  async function add(kind: "food" | "dish" | "text", code: string) {
    setErr(null);
    try {
      await post("/preferences/dislikes", { kind, code });
      setQ("");
      await refresh();
    } catch (x) {
      setErr(errorMessage(x, t));
    }
  }
  async function remove(id: number) {
    setErr(null);
    try {
      await del(`/preferences/dislikes/${id}`);
      await refresh();
    } catch (x) {
      setErr(errorMessage(x, t));
    }
  }

  return (
    <section className="card">
      <h3>{t.dislikes.title}</h3>
      <p className="small muted">{t.dislikes.help}</p>
      <div className="chips">
        {(list.data ?? []).map((d) => (
          <span key={d.id} className="chip on">
            {d.name}{d.kind === "dish" ? ` (${t.dislikes.dish})` : d.kind === "text" ? ` (${t.dislikes.text})` : ""}
            <button type="button" className="chip-x" aria-label={fmt(t.dislikes.remove, { name: d.name })}
                    onClick={() => remove(d.id)}>{"\u00d7"}</button>
          </span>
        ))}
        {list.data?.length === 0 && <span className="small muted">{t.dislikes.empty}</span>}
      </div>
      <label>{t.dislikes.search}
        <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.dislikes.placeholder} />
      </label>
      {needle && results.length === 0 && q.trim().length <= 40 && (
        <button type="button" className="link" onClick={() => add("text", q.trim())}>
          {fmt(t.dislikes.addText, { name: q.trim() })}
        </button>
      )}
      {results.length > 0 && (
        <ul className="items">
          {results.map((o) => (
            <li key={`${o.kind}:${o.code}`}>
              <span>{o.name}{o.kind === "dish" ? ` (${t.dislikes.dish})` : ""}</span>
              <button type="button" className="link" onClick={() => add(o.kind, o.code)}>{t.dislikes.add}</button>
            </li>
          ))}
        </ul>
      )}
      {err && <p className="error">{err}</p>}
    </section>
  );
}
