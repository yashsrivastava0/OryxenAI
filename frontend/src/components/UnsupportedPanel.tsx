export interface UnsupportedPanelProps {
  stageName: string;
  statusText: string;
}

export function UnsupportedPanel({ stageName, statusText }: UnsupportedPanelProps) {
  return (
    <section className="unsupported-panel" role="alert">
      <p className="eyebrow">State check</p>
      <h2>{stageName} returned an unfamiliar state</h2>
      <p>{statusText}</p>
      <p className="unsupported-note">No action has been guessed or submitted. Refresh after the application has been updated.</p>
      <button type="button" className="btn-secondary" onClick={() => window.location.reload()}>
        Refresh workspace
      </button>
    </section>
  );
}
