import { useState } from "preact/hooks";
import type { DiscoveryQuestionOption } from "../data/adapters/discovery";
import "../styles/theme-picker.css";

interface ThemePickerProps {
  options: DiscoveryQuestionOption[];
  questionId: string;
  label: string;
  selectedId: string | null;
  disabled: boolean;
  onSelect: (id: string) => void;
}

export function ThemePicker({ options, questionId, label, selectedId, disabled, onSelect }: ThemePickerProps) {
  const [query, setQuery] = useState("");
  const [collection, setCollection] = useState("all");
  const selected = options.find((option) => option.id === selectedId);
  const term = query.trim().toLocaleLowerCase();
  const visible = options.filter((option) =>
    (collection === "all" || (option.theme?.collection ?? "classic") === collection)
    && `${option.label} ${option.description} ${option.theme?.badge ?? ""}`.toLocaleLowerCase().includes(term),
  );
  return (
    <div className="theme-picker">
      <div className="theme-picker__toolbar">
        <div className="theme-picker__filters" role="group" aria-label="Filter portfolio looks">
          {([["all", "All looks"], ["interactive", "Interactive"], ["classic", "Classic"]] as const).map(([id, text]) => (
            <button key={id} type="button" aria-pressed={collection === id} disabled={disabled} onClick={() => setCollection(id)}>{text}</button>
          ))}
        </div>
        <input type="search" aria-label="Search portfolio looks" placeholder="Search looks" value={query} disabled={disabled} maxLength={100} onInput={(event) => setQuery(event.currentTarget.value)} />
      </div>
      <div className="theme-picker__status" role="status">{visible.length} {visible.length === 1 ? "look" : "looks"}{term || collection !== "all" ? ` of ${options.length}` : " available"}</div>
      <div className="theme-picker__gallery" role="region" aria-label="Portfolio looks" tabIndex={0}>
        <div role="radiogroup" aria-label={label}>
          {(["interactive", "classic"] as const).map((group) => {
            const choices = visible.filter((option) => (option.theme?.collection ?? "classic") === group);
            if (!choices.length) return null;
            return (
              <section key={group} className="theme-picker__collection" aria-label={group === "interactive" ? "Interactive looks" : "Classic looks"}>
                <div className="theme-picker__heading"><strong>{group === "interactive" ? "Motion & interaction" : "Classic looks"}</strong><span>{group === "interactive" ? "Scroll, depth and interactive pages" : "Simple, focused layouts"}</span></div>
                <div className="palette-choice-list">
                  {choices.map((option) => {
                    const colors = option.theme?.colors ?? option.swatches;
                    const isSelected = selectedId === option.id;
                    return (
                      <label key={option.id} data-look={option.id} data-preview={option.theme?.style ?? "editorial"} className={`palette-choice ${isSelected ? "is-selected" : ""}`} style={{ "--demo-bg": colors[0] ?? "#14231c", "--demo-ink": colors[1] ?? "#f3f1e9", "--demo-accent": colors[2] ?? "#9a3f29" }}>
                        <input type="radio" name={`discovery-q-${questionId}`} aria-label={option.label} aria-describedby={`${questionId}-${option.id}-detail`} className="visually-hidden choice-input" checked={isSelected} disabled={disabled} onChange={() => onSelect(option.id)} />
                        <span className="palette-choice__demo" aria-hidden="true">
                          <span className="palette-demo__top"><i /><i /><i /></span>
                          <span className="palette-demo__body"><span className="palette-demo__eyebrow" /><span className="palette-demo__headline"><span /><span /><span /></span><span className="palette-demo__accent" /><span className="palette-demo__detail"><i /><i /><i /></span></span>
                        </span>
                        <span className="palette-choice__swatches" aria-hidden="true">{option.swatches.map((color, index) => <span key={index} style={{ backgroundColor: color }} />)}</span>
                        <span className="palette-choice__footer"><span><strong>{option.label}</strong><small id={`${questionId}-${option.id}-detail`}>{option.description}</small>{option.theme?.badge && <em>{option.theme.badge}</em>}</span><span className="palette-choice__check" aria-hidden="true">{isSelected ? "✓" : "○"}</span></span>
                      </label>
                    );
                  })}
                </div>
              </section>
            );
          })}
          {!visible.length && <div className="theme-picker__empty"><strong>No matching looks</strong><p>Try a different search or view all looks.</p><button type="button" disabled={disabled} onClick={() => { setQuery(""); setCollection("all"); }}>Clear filters</button></div>}
        </div>
      </div>
      <div className="theme-picker__selection" aria-live="polite"><span>{selected ? "Selected look" : "Choose a look to continue"}</span>{selected && <strong>{selected.label}</strong>}{selected && !visible.some((option) => option.id === selected.id) && <button type="button" disabled={disabled} onClick={() => { setQuery(""); setCollection("all"); }}>Show selection</button>}</div>
    </div>
  );
}
