import { useEffect, useState } from "preact/hooks";
import type { DiscoveryQuestionVM } from "../data/adapters/discovery";
import {
  answeredDiscoveryQuestion,
  skippedDiscoveryQuestion,
  type DiscoveryAnswerSubmission,
} from "../data/discovery-answer";
import { safeSessionStorage } from "../data/safe-storage";
import { captureFailure, type FailureDiagnosticInput } from "../data/failure-diagnostics";
import { CopyDiagnosticsButton } from "./CopyDiagnosticsButton";
import { ActionDock } from "./ActionDock";
import { HelpDisclosure } from "./HelpDisclosure";

// Looks whose design includes scripted, interactive pages carry a short tag on their card.
const PALETTE_TAGS: Record<string, string> = {
  cobalt_atlas_interactive: "Interactive details",
  claret_amber: "Cinematic motion",
};

interface DiscoveryQuestionCardProps {
  question: DiscoveryQuestionVM;
  ordinal: number;
  total: number;
  isLast: boolean;
  disabled: boolean;
  onSubmitAnswer: (answer: DiscoveryAnswerSubmission, isComplete: boolean) => Promise<void>;
}

export function DiscoveryQuestionCard({
  question,
  ordinal,
  total,
  isLast,
  disabled,
  onSubmitAnswer,
}: DiscoveryQuestionCardProps) {
  const [textAnswer, setTextAnswer] = useState("");
  const [selectedSingleOption, setSelectedSingleOption] = useState<string | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<string[]>([]);
  const [allowIllustrative, setAllowIllustrative] = useState(false);
  const [inFlight, setInFlight] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [failure, setFailure] = useState<FailureDiagnosticInput | null>(null);
  const draftKey = `oryxenai.draft.${question.id}`;
  const singleKey = `${draftKey}.single`;
  const multiKey = `${draftKey}.multi`;
  const illustrativeKey = `${draftKey}.illustrative`;
  const locked = disabled || inFlight;
  const questionOrdinalText = `Question ${String(ordinal).padStart(2, "0")} of ${String(total).padStart(2, "0")}`;
  const canSubmit = question.kind === "palette_select"
    ? Boolean(selectedSingleOption)
    : question.kind === "work_detail"
      ? Boolean(textAnswer.trim() || allowIllustrative)
    : Boolean(textAnswer.trim() || selectedSingleOption || selectedOptions.length > 0);

  useEffect(() => {
    setTextAnswer(safeSessionStorage.getItem(draftKey) ?? "");
    setSelectedSingleOption(safeSessionStorage.getItem(singleKey));
    setAllowIllustrative(safeSessionStorage.getItem(illustrativeKey) === "true");
    const savedOptions = safeSessionStorage.getItem(multiKey);
    try {
      const parsed: unknown = JSON.parse(savedOptions ?? "[]");
      setSelectedOptions(Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === "string") : []);
    } catch {
      setSelectedOptions([]);
    }
    setError(null);
    setFailure(null);
  }, [draftKey, singleKey, multiKey, illustrativeKey]);

  const updateText = (value: string) => {
    setTextAnswer(value);
    safeSessionStorage.setItem(draftKey, value);
  };

  const clearDraft = () => {
    safeSessionStorage.removeItem(draftKey);
    safeSessionStorage.removeItem(singleKey);
    safeSessionStorage.removeItem(multiKey);
    safeSessionStorage.removeItem(illustrativeKey);
    setTextAnswer("");
    setSelectedSingleOption(null);
    setSelectedOptions([]);
    setAllowIllustrative(false);
  };

  const submit = async (skip = false) => {
    if (locked || (!skip && !canSubmit)) return;
    const selectedValue = question.kind === "multi_select"
      ? selectedOptions
      : selectedSingleOption;
    const selectedIds = Array.isArray(selectedValue)
      ? selectedValue
      : selectedValue ? [selectedValue] : [];
    const choiceLabels = new Map(question.options.map((option) => [option.id, option.label]));
    const selectedText = selectedIds.map((id) =>
      question.kind === "boolean" ? (id === "true" ? "Yes" : "No") : choiceLabels.get(id) ?? id,
    ).join(", ");
    const customText = textAnswer.trim();
    const value = question.kind === "palette_select"
      ? { choice_id: selectedSingleOption, note: customText }
      : question.kind === "work_detail"
        ? { details: customText, allow_illustrative: allowIllustrative }
      : customText
        ? selectedText ? `${selectedText}. ${customText}` : customText
        : selectedValue;
    const answer = skip
      ? skippedDiscoveryQuestion(question.id)
      : answeredDiscoveryQuestion(question.id, value);
    setInFlight(true);
    setError(null);
    try {
      await onSubmitAnswer(answer, isLast);
      clearDraft();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "We couldn't save that answer. Try again.");
      setFailure(captureFailure(reason, "discovery", "answer question", "We couldn't save that answer. Try again."));
    } finally {
      setInFlight(false);
    }
  };

  const onComposerKeyDown = (event: KeyboardEvent) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      void submit();
    }
  };

  return (
    <div className="discovery-workbench-card active-question-card">
      <div className="workbench-top-rule" aria-hidden="true">
        <span className="workbench-sweep" />
      </div>
      <div className="question-content">
        <div className="question-header">
          <div className="question-eyebrow-row">
            <span className="question-stage-tag">EXPLORER</span>
            <span className="question-ordinal">{questionOrdinalText}</span>
          </div>
          <h2 className="question-prompt">{question.text}</h2>
          {question.helpText && <div className="question-help-row"><p className="question-help">{question.helpText}</p><HelpDisclosure label="this question">Your answer helps shape the brief. You can review it before the next stage begins.</HelpDisclosure></div>}
        </div>

        {error && <div className="discovery-error-callout" role="alert">{error} {failure && <CopyDiagnosticsButton failure={failure} />}</div>}

        {question.kind === "single_select" && (
          <fieldset className="choice-fieldset">
            <legend className="choice-group-hint">SELECT ONE</legend>
            <div className="choice-list" role="radiogroup" aria-label={question.text}>
              {question.options.map((option) => {
                const selected = selectedSingleOption === option.id;
                return (
                  <label key={option.id} className={`choice-tile ${selected ? "is-selected" : ""}`}>
                    <input
                      type="radio"
                      name={`discovery-q-${question.id}`}
                      className="visually-hidden choice-input"
                      checked={selected}
                      disabled={locked}
                      onChange={() => {
                        setSelectedSingleOption(option.id);
                        safeSessionStorage.setItem(singleKey, option.id);
                      }}
                    />
                    <span className="choice-indicator choice-indicator--radio" aria-hidden="true">
                      {selected && <span className="choice-radio-dot" />}
                    </span>
                    <span className="choice-text">{option.label}</span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        )}

        {question.kind === "palette_select" && (
          <fieldset className="choice-fieldset palette-fieldset">
            <legend className="choice-group-hint">CHOOSE YOUR COMPLETE LOOK</legend>
            <div className="palette-intro">Choose the color, type, and layout direction that feels most like you. <HelpDisclosure label="visual direction">Each choice sets the overall look of your page. You will review the content before your page is built.</HelpDisclosure></div>
            <div className="palette-choice-list" role="radiogroup" aria-label={question.text}>
              {question.options.map((option) => {
                const selected = selectedSingleOption === option.id;
                return (
                  <label key={option.id} data-look={option.id} className={`palette-choice ${selected ? "is-selected" : ""}`}>
                    <input
                      type="radio"
                      name={`discovery-q-${question.id}`}
                      className="visually-hidden choice-input"
                      checked={selected}
                      disabled={locked}
                      onChange={() => {
                        setSelectedSingleOption(option.id);
                        safeSessionStorage.setItem(singleKey, option.id);
                      }}
                    />
                    <span className="palette-choice__demo" aria-hidden="true">
                      <span className="palette-demo__top"><i /><i /><i /></span>
                      <span className="palette-demo__body">
                        <span className="palette-demo__eyebrow" />
                        <span className="palette-demo__headline"><span /><span /><span /></span>
                        <span className="palette-demo__accent" />
                        <span className="palette-demo__detail"><i /><i /><i /></span>
                      </span>
                    </span>
                    <span className="palette-choice__swatches" aria-hidden="true">
                      {option.swatches.map((color) => <span key={color} style={{ backgroundColor: color }} />)}
                    </span>
                    <span className="palette-choice__footer">
                      <span><strong>{option.label}</strong><small>{option.description}</small>{PALETTE_TAGS[option.id] && <em>{PALETTE_TAGS[option.id]}</em>}</span>
                      <span className="palette-choice__check" aria-hidden="true">{selected ? "✓" : "○"}</span>
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        )}

        {question.kind === "boolean" && (
          <fieldset className="choice-fieldset">
            <legend className="choice-group-hint">SELECT ONE</legend>
            <div className="choice-list boolean-choice-list" role="radiogroup" aria-label={question.text}>
              {[
                { id: "true", label: "Yes" },
                { id: "false", label: "No" },
              ].map((option) => {
                const selected = selectedSingleOption === option.id;
                return (
                  <label key={option.id} className={`choice-tile ${selected ? "is-selected" : ""}`}>
                    <input
                      type="radio"
                      name={`discovery-q-${question.id}`}
                      className="visually-hidden choice-input"
                      checked={selected}
                      disabled={locked}
                      onChange={() => {
                        setSelectedSingleOption(option.id);
                        safeSessionStorage.setItem(singleKey, option.id);
                      }}
                    />
                    <span className="choice-indicator choice-indicator--radio" aria-hidden="true">
                      {selected && <span className="choice-radio-dot" />}
                    </span>
                    <span className="choice-text">{option.label}</span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        )}

        {question.kind === "multi_select" && (
          <fieldset className="choice-fieldset">
            <legend className="choice-group-hint">SELECT ALL THAT APPLY</legend>
            <div className="choice-list" role="group" aria-label={question.text}>
              {question.options.map((option) => {
                const selected = selectedOptions.includes(option.id);
                return (
                  <label key={option.id} className={`choice-tile ${selected ? "is-selected" : ""}`}>
                    <input
                      type="checkbox"
                      className="visually-hidden choice-input"
                      checked={selected}
                      disabled={locked}
                      onChange={(event) => {
                        const checked = (event.target as HTMLInputElement).checked;
                        setSelectedOptions((previous) => {
                          const next = checked
                            ? [...previous, option.id]
                            : previous.filter((id) => id !== option.id);
                          safeSessionStorage.setItem(multiKey, JSON.stringify(next));
                          return next;
                        });
                      }}
                    />
                    <span className="choice-indicator choice-indicator--checkbox" aria-hidden="true">
                      {selected && (
                        <svg width="12" height="10" viewBox="0 0 12 10" fill="none" aria-hidden="true">
                          <path d="M1 5L4.5 8.5L11 1.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                        </svg>
                      )}
                    </span>
                    <span className="choice-text">{option.label}</span>
                  </label>
                );
              })}
            </div>
          </fieldset>
        )}

        {question.kind === "work_detail" && (
          <label className="choice-tile">
            <input
              type="checkbox"
              checked={allowIllustrative}
              disabled={locked}
              onChange={(event) => {
                const checked = (event.target as HTMLInputElement).checked;
                setAllowIllustrative(checked);
                safeSessionStorage.setItem(illustrativeKey, String(checked));
              }}
            />
            <span>If I have no usable real project, show a clearly labeled illustrative concept.</span>
          </label>
        )}
        <div className="text-composer-group">
            <label className="choice-group-hint composer-label" htmlFor={`discovery-answer-${question.id}`}>
              {question.kind === "text" ? "Your answer" : question.kind === "palette_select" ? "Optional note for your reference" : question.kind === "work_detail" ? "Optional real project details" : "Add context or write your own answer"}
            </label>
            <textarea
              maxLength={question.kind === "palette_select" ? 1000 : undefined}
              id={`discovery-answer-${question.id}`}
              className="workbench-textarea composer-textarea"
              rows={question.kind === "text" || question.kind === "work_detail" ? 4 : 3}
              placeholder={question.kind === "text" ? "Write what feels important…" : question.kind === "palette_select" ? "A detail you want to remember about this look…" : question.kind === "work_detail" ? "Project name, problem, your contribution, approach and outcome, if known…" : "Optional details, or a different answer…"}
              value={textAnswer}
              onInput={(event) => updateText((event.target as HTMLTextAreaElement).value)}
              onKeyDown={onComposerKeyDown}
              disabled={locked}
            />
            {Boolean(textAnswer.trim()) && <div className="draft-status-row" aria-live="polite">Draft saved</div>}
        </div>

        <ActionDock
          primaryLabel={isLast ? "Continue to brief" : "Next question"}
          busyLabel="Saving answer…"
          busy={inFlight}
          disabled={locked || !canSubmit}
          onPrimary={() => submit()}
          note={questionOrdinalText}
        >
          {question.allowSkip && <button type="button" className="btn-quiet btn-skip-question" disabled={locked} onClick={() => void submit(true)}>Skip question</button>}
        </ActionDock>
      </div>
    </div>
  );
}
