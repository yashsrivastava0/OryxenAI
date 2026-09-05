interface CacheNoticeProps {
  message: string | null;
}

/** A short, non-blocking explanation when a completed response was reused. */
export function CacheNotice({ message }: CacheNoticeProps) {
  if (!message) return null;
  return (
    <div className="cache-notice" role="status" aria-live="polite">
      <span className="cache-notice-mark" aria-hidden="true">✦</span>
      <span>{message}</span>
    </div>
  );
}
