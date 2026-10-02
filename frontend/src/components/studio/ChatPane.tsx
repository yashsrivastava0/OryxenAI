import { useEffect, useRef, useState } from "preact/hooks";
import {
  readyVersions,
  studioStageLabel,
  type StudioChatVM,
  type StudioFailureVM,
  type StudioInFlightVM,
  type StudioVersionVM,
} from "../../data/adapters/studio";
import { FailurePanel } from "./FailurePanel";

export const MAX_MESSAGE_CHARS = 1500;

const SUGGESTIONS = [
  "Make my introduction a bit shorter",
  "Add a link to my blog",
  "Reword my headline",
  "Add Rust to my keywords",
];

export interface ChatPaneProps {
  chat: StudioChatVM[];
  versions: StudioVersionVM[];
  activeVersionId: string | null;
  inFlight: StudioInFlightVM | null;
  lastError: StudioFailureVM | null;
  /** A studio request (send, restore, stop) is in progress. */
  busy: boolean;
  onSend: (message: string, clientMessageId: string) => Promise<void>;
  onStop: () => Promise<void>;
  onRestore: (versionId: string) => Promise<void>;
}

function timeLabel(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function originLabel(version: StudioVersionVM): string {
  if (version.origin === "restore") return "Restored";
  if (version.origin === "change") return version.instruction || "Change";
  return "First build";
}

export function ChatPane({
  chat,
  versions,
  activeVersionId,
  inFlight,
  lastError,
  busy,
  onSend,
  onStop,
  onRestore,
}: ChatPaneProps) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [showFailure, setShowFailure] = useState(false);
  const logRef = useRef<HTMLDivElement | null>(null);
  const attemptId = useRef<string | null>(null);

  const building = inFlight !== null;
  const locked = building || busy || sending;
  const numbers = new Map(versions.map((item) => [item.id, item.versionNumber]));
  const history = readyVersions(versions);
  const hasUserMessage = chat.some((item) => item.role === "user");
  const tooLong = draft.length > MAX_MESSAGE_CHARS;
  const canSend = draft.trim().length > 0 && !tooLong && !locked;

  useEffect(() => {
    const element = logRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, [chat.length, building]);

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || locked || message.length > MAX_MESSAGE_CHARS) return;
    // One id per attempt: a retried send after a lost response is not duplicated.
    attemptId.current ??= `m-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    setSending(true);
    setSendError(null);
    try {
      await onSend(message, attemptId.current);
      attemptId.current = null;
      setDraft("");
    } catch (error) {
      setSendError(error instanceof Error ? error.message : "Your message could not be sent.");
    } finally {
      setSending(false);
    }
  };

  const restore = async (versionId: string) => {
    setRestoreError(null);
    try {
      await onRestore(versionId);
    } catch (error) {
      setRestoreError(error instanceof Error ? error.message : "That version could not be restored.");
    }
  };

  return (
    <section className="studio-chat" aria-label="Change your portfolio">
      <header className="studio-chat-head">
        <span className="eyebrow">Changes</span>
        <h2>Tell me what to change</h2>
        <p>I can change the words on your page: wording, keywords, skills, organizations, links and the title. Colors and layout are not available yet.</p>
      </header>

      <div className="studio-chat-log" ref={logRef} role="log" aria-live="polite" aria-label="Conversation">
        {chat.length === 0 ? (
          <p className="studio-chat-empty">
            Your page is ready. Ask for a change in plain language, for example “Make my introduction a bit shorter”.
          </p>
        ) : null}
        {chat.map((message) => {
          const number = message.versionId ? numbers.get(message.versionId) : null;
          return (
            <div key={message.id} className={`studio-msg studio-msg--${message.role} studio-msg--${message.kind}`}>
              <p>{message.body}</p>
              <footer>
                {number ? <span className="studio-chip">v{number}</span> : null}
                <time dateTime={message.createdAt ?? undefined}>{timeLabel(message.createdAt)}</time>
              </footer>
            </div>
          );
        })}
        {building && inFlight ? (
          <div className="studio-msg studio-msg--assistant studio-msg--working" role="status">
            <span className="pulse-indicator" aria-hidden="true" />
            <p>{studioStageLabel(inFlight.stage, inFlight.origin)}…</p>
            <button type="button" className="btn-quiet" onClick={() => void onStop()} disabled={busy}>
              Stop
            </button>
          </div>
        ) : null}
      </div>

      {lastError && !building && lastError.code !== "JOB_CANCELLED" ? (
        <div className="studio-chat-failure">
          <button
            type="button"
            className="studio-failure-toggle"
            aria-expanded={showFailure}
            onClick={() => setShowFailure((open) => !open)}
          >
            {showFailure ? "Hide details" : "See exactly what went wrong"}
          </button>
          {showFailure ? (
            <FailurePanel
              failure={lastError}
              compact
              title="That change did not go through"
              preservedNote="Your live page is unchanged. Ask again, or word the change differently."
            />
          ) : null}
        </div>
      ) : null}

      {history.length > 1 ? (
        <details className="studio-versions">
          <summary>Versions ({history.length})</summary>
          <ul>
            {history.map((version) => {
              const live = version.id === activeVersionId;
              return (
                <li key={version.id} className={live ? "is-live" : ""}>
                  <span className="studio-chip">v{version.versionNumber}</span>
                  <span className="studio-version-label">{originLabel(version)}</span>
                  <time dateTime={version.completedAt ?? undefined}>{timeLabel(version.completedAt)}</time>
                  {live ? (
                    <span className="studio-pill">Live</span>
                  ) : version.restricted ? (
                    <span className="studio-pill studio-pill--muted" title="Removed because it showed information you asked to hide">
                      Removed
                    </span>
                  ) : (
                    <button type="button" className="btn-quiet" disabled={locked} onClick={() => void restore(version.id)}>
                      Restore
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
          {restoreError ? <p className="studio-inline-error" role="alert">{restoreError}</p> : null}
        </details>
      ) : null}

      <form
        className="studio-composer"
        onSubmit={(event) => {
          event.preventDefault();
          void send(draft);
        }}
      >
        {!hasUserMessage && !building ? (
          <div className="studio-suggestions" aria-label="Suggestions">
            {SUGGESTIONS.map((text) => (
              <button key={text} type="button" className="studio-suggestion" disabled={locked} onClick={() => void send(text)}>
                {text}
              </button>
            ))}
          </div>
        ) : null}
        <label className="visually-hidden" htmlFor="studio-message">Describe the change you want</label>
        <textarea
          id="studio-message"
          rows={3}
          value={draft}
          maxLength={MAX_MESSAGE_CHARS + 200}
          placeholder={building ? "Wait for the current change to finish…" : "Describe a change to the words on your page"}
          disabled={locked}
          onInput={(event) => setDraft((event.target as HTMLTextAreaElement).value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
              event.preventDefault();
              void send(draft);
            }
          }}
        />
        <div className="studio-composer-row">
          <span className={`studio-count${tooLong ? " is-over" : ""}`} aria-live="polite">
            {draft.length > 1200 ? `${draft.length}/${MAX_MESSAGE_CHARS}` : ""}
          </span>
          <button type="submit" className="btn-primary" disabled={!canSend}>
            {sending ? "Sending…" : "Send"}
          </button>
        </div>
        {sendError ? <p className="studio-inline-error" role="alert">{sendError}</p> : null}
      </form>
    </section>
  );
}
