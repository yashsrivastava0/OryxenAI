// One polite live region for the whole app (docs/Frontend/05 §8.12). Only
// meaningful state transitions should be pushed into `message` — never
// timers, every poll, or every activity item.
interface StatusAnnouncerProps {
  message: string | null;
}

export function StatusAnnouncer({ message }: StatusAnnouncerProps) {
  return (
    <div role="status" aria-live="polite" className="visually-hidden">
      {message}
    </div>
  );
}
