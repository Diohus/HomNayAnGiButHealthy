import { useI18n, LANG_NAMES, LANGS, type Lang } from "../i18n";
import { getTheme, setTheme, THEMES, type Theme } from "../theme";
import { useState } from "react";

// Radio group in <fieldset>/<legend>: arrow keys select, screen readers announce the group.
function RadioGroup<V extends string>({ name, legend, value, options, onChange }: {
  name: string; legend: string; value: V; options: readonly (readonly [V, string])[]; onChange: (v: V) => void;
}) {
  return (
    <fieldset>
      <legend>{legend}</legend>
      <div className="seg">
        {options.map(([v, label]) => (
          <label key={v} className={value === v ? "on" : ""}>
            <input type="radio" name={name} value={v} checked={value === v} onChange={() => onChange(v)} />
            {label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

export function LanguagePicker() {
  const { lang, setLang, t } = useI18n();
  return (
    <RadioGroup<Lang> name="lang" legend={t.settings.language} value={lang} onChange={setLang}
                      options={LANGS.map((l) => [l, LANG_NAMES[l]] as const)} />
  );
}

export function ThemePicker() {
  const { t } = useI18n();
  const [theme, set] = useState<Theme>(getTheme);
  return (
    <RadioGroup<Theme> name="theme" legend={t.settings.appearance} value={theme}
                       onChange={(v) => { setTheme(v); set(v); }}
                       options={THEMES.map((v) => [v, t.settings.themes[v]] as const)} />
  );
}
