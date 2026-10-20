import { useEffect, useState } from "preact/hooks";
import type { ApiClient, ReactHandoff } from "../../data/api-client";

const pending = (row: ReactHandoff | null) =>
  !!row && ["queued", "preparing", "validating"].includes(row.status);

export function HandoffPanel({
  api,
  sessionId,
  versionId,
  disabled,
}: {
  api: ApiClient;
  sessionId: string;
  versionId: string;
  disabled: boolean;
}) {
  const [rows, setRows] = useState<ReactHandoff[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const preparing = rows.find((row) => pending(row)) ?? null;
  const ready = rows.find(
    (row) =>
      row.status === "ready" &&
      row.expires_at &&
      Date.parse(row.expires_at) > Date.now(),
  );
  const current =
    rows.find((row) => row.source_version_id === versionId) ?? null;
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const result = await api.listHandoffs(sessionId);
        if (!cancelled) {
          setRows(result.handoffs);
          timer = setTimeout(
            () => void refresh(),
            result.handoffs.some((row) => pending(row)) ? 2000 : 30000,
          );
        }
      } catch {
        if (!cancelled) {
          setMessage(
            "Sharing status could not be refreshed. Try again shortly.",
          );
          timer = setTimeout(() => void refresh(), 10000);
        }
      }
    };
    void refresh();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [api, sessionId, preparing?.id]);
  const act = async (operation: () => Promise<ReactHandoff>) => {
    setBusy(true);
    setMessage("");
    try {
      const row = await operation();
      setRows((old) =>
        [row, ...old.filter((item) => item.id !== row.id)].slice(0, 3),
      );
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Sharing could not be updated.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="studio-handoff" aria-label="React handoff">
      <div>
        <strong>Continue in your coding agent</strong>
        <p>
          Prepare a complete React project for MCP sharing. The link lasts 24
          hours; imported copies remain with the recipient.
        </p>
      </div>
      <button
        type="button"
        className="btn-secondary"
        disabled={
          disabled || busy || !!preparing || current?.status === "ready"
        }
        onClick={() => void act(() => api.prepareHandoff(sessionId, versionId))}
      >
        {preparing
          ? "Preparing React handoff…"
          : current?.status === "ready"
            ? "React handoff ready"
            : ready
              ? "Prepare replacement handoff"
              : "Prepare React handoff"}
      </button>
      {ready?.share_link && (
        <div className="studio-handoff-link">
          <label>
            Share link
            <input
              readOnly
              value={ready.share_link}
              onFocus={(event) => event.currentTarget.select()}
            />
          </label>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => {
              void navigator.clipboard.writeText(ready.share_link!).then(
                () => setMessage("Share link copied."),
                () => setMessage("Select and copy the share link."),
              );
            }}
          >
            Copy link
          </button>
          <p>
            Connect your agent to <code>{ready.mcp_url}</code>, then ask it to
            import this share link. Expires{" "}
            {new Date(ready.expires_at!).toLocaleString()}.
          </p>
          <button
            type="button"
            className="btn-secondary"
            disabled={busy}
            onClick={() =>
              void act(() => api.revokeHandoff(sessionId, ready.id))
            }
          >
            Revoke link
          </button>
        </div>
      )}
      {current?.status === "failed" && (
        <p role="alert">
          {current.error?.message ?? "Preparation failed. You can try again."}
          {ready ? " Your previous link still works." : ""}
        </p>
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
