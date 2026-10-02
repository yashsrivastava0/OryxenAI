import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import type { StudioPreviewGrant } from "../../data/api-client";

export type PreviewDevice = "desktop" | "tablet" | "mobile";

const DEVICES: Array<{ id: PreviewDevice; label: string; width: number }> = [
  { id: "desktop", label: "Desktop", width: 1280 },
  { id: "tablet", label: "Tablet", width: 768 },
  { id: "mobile", label: "Mobile", width: 390 },
];

interface PreviewFrame {
  key: number;
  url: string;
  ready: boolean;
}

export interface PreviewPaneProps {
  versionId: string | null;
  versionNumber: number;
  /** Mints a short-lived signed preview URL for a ready version. */
  loadPreview: (versionId: string) => Promise<StudioPreviewGrant>;
  /** A change is being built: the current page stays until the new one loads. */
  updating?: boolean;
}

const GRANT_MARGIN_MS = 60_000;

export function previewScale(paneWidth: number, deviceWidth: number, fit: boolean): number {
  if (!fit || paneWidth <= 0) return 1;
  return Math.max(0.2, Math.min(1, (paneWidth - 24) / deviceWidth));
}

/**
 * The live page in a sandboxed frame. The browser keeps showing the current
 * version until the next one has finished loading (two frames, swapped on load),
 * so an update never blanks the preview.
 */
export function PreviewPane({ versionId, versionNumber, loadPreview, updating = false }: PreviewPaneProps) {
  const [device, setDevice] = useState<PreviewDevice>("desktop");
  const [fit, setFit] = useState(true);
  const [frames, setFrames] = useState<PreviewFrame[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [reloadNonce, setReloadNonce] = useState(0);
  const [host, setHost] = useState({ width: 0, height: 0 });
  const hostRef = useRef<HTMLDivElement | null>(null);
  const keyRef = useRef(0);
  const grantRef = useRef<{ url: string; expiresAt: number } | null>(null);

  useLayoutEffect(() => {
    const element = hostRef.current;
    if (!element) return undefined;
    const apply = () => setHost({ width: element.clientWidth, height: element.clientHeight });
    apply();
    if (typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver(apply);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!versionId) return undefined;
    let cancelled = false;
    setLoading(true);
    setError(null);
    void loadPreview(versionId)
      .then((grant) => {
        if (cancelled) return;
        grantRef.current = {
          url: grant.url,
          expiresAt: Date.now() + Math.max(0, grant.expires_in_seconds) * 1000,
        };
        keyRef.current += 1;
        const key = keyRef.current;
        setFrames((previous) => [...previous.filter((frame) => frame.ready).slice(-1), { key, url: grant.url, ready: false }]);
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        setLoading(false);
        setError(reason instanceof Error ? reason.message : "The preview could not be loaded.");
      });
    return () => {
      cancelled = true;
    };
  }, [versionId, reloadNonce, loadPreview]);

  const onFrameLoad = useCallback((key: number) => {
    setLoading(false);
    setFrames((previous) =>
      previous
        .map((frame) => (frame.key === key ? { ...frame, ready: true } : frame))
        .filter((frame, _index, all) => !(frame.ready && all.some((other) => other.ready && other.key > frame.key))),
    );
  }, []);

  const current = [...frames].reverse().find((frame) => frame.ready) ?? null;
  const spec = DEVICES.find((item) => item.id === device) ?? DEVICES[0]!;
  const scale = previewScale(host.width, spec.width, fit);
  const frameHeight = Math.max(480, (host.height - 24) / (fit ? scale : 1));

  const openStandalone = async (event: MouseEvent) => {
    const grant = grantRef.current;
    if (!versionId || (grant && grant.expiresAt - Date.now() > GRANT_MARGIN_MS)) return; // plain link
    event.preventDefault();
    try {
      const fresh = await loadPreview(versionId);
      window.open(fresh.url, "_blank", "noopener,noreferrer");
    } catch {
      setError("The preview link could not be refreshed. Try Reload.");
    }
  };

  return (
    <section className="studio-preview" aria-label="Live portfolio preview">
      <header className="studio-preview-bar">
        <div className="studio-preview-title">
          <span className="eyebrow">Live preview</span>
          <strong>{versionNumber > 0 ? `Version ${versionNumber}` : "Your portfolio"}</strong>
          {updating ? (
            <span className="studio-pill studio-pill--busy" role="status">
              <span className="pulse-indicator" aria-hidden="true" />
              Updating…
            </span>
          ) : null}
        </div>

        <div className="studio-preview-tools">
          <div className="studio-segment" role="group" aria-label="Preview size">
            {DEVICES.map((item) => (
              <button
                key={item.id}
                type="button"
                className={device === item.id ? "is-active" : ""}
                aria-pressed={device === item.id}
                onClick={() => setDevice(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="studio-segment" role="group" aria-label="Zoom">
            <button type="button" className={fit ? "is-active" : ""} aria-pressed={fit} onClick={() => setFit(true)}>
              Fit
            </button>
            <button type="button" className={!fit ? "is-active" : ""} aria-pressed={!fit} onClick={() => setFit(false)}>
              100%
            </button>
          </div>
          <button type="button" className="btn-quiet" onClick={() => setReloadNonce((count) => count + 1)} disabled={!versionId}>
            Reload
          </button>
          {current ? (
            <a
              className="btn-quiet"
              href={current.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(event) => void openStandalone(event as unknown as MouseEvent)}
            >
              Open in new tab ↗
            </a>
          ) : null}
        </div>
      </header>

      <div className="studio-preview-stage" ref={hostRef} data-fit={fit ? "true" : "false"}>
        {error ? (
          <div className="studio-preview-note" role="alert">
            <p>{error}</p>
            <button type="button" className="btn-secondary" onClick={() => setReloadNonce((count) => count + 1)}>
              Try again
            </button>
          </div>
        ) : null}
        {!error && !current ? (
          <div className="studio-preview-note" role="status">
            <span className="pulse-indicator" aria-hidden="true" />
            <p>{loading ? "Opening your page…" : "Your page will appear here."}</p>
          </div>
        ) : null}
        <div
          className="studio-device"
          style={{ width: `${spec.width * scale}px`, height: `${frameHeight * scale}px` }}
          data-device={device}
        >
          {frames.map((frame) => {
            const visible = current !== null && frame.key === current.key;
            return (
              <iframe
                key={frame.key}
                className={`studio-frame${visible ? " is-visible" : ""}`}
                title="Portfolio preview"
                src={frame.url}
                sandbox="allow-popups allow-popups-to-escape-sandbox"
                referrerPolicy="no-referrer"
                style={{
                  width: `${spec.width}px`,
                  height: `${frameHeight}px`,
                  transform: `scale(${scale})`,
                }}
                onLoad={() => onFrameLoad(frame.key)}
              />
            );
          })}
        </div>
      </div>
    </section>
  );
}
