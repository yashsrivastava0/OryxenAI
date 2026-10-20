import { useEffect, useState } from "react";

/** Bounded React-owned intro. Fonts, timers and effects are cleaned up. */
export function Intro({
  enabled,
  claret,
  name,
  monogram,
}: {
  enabled: boolean;
  claret: boolean;
  name: string;
  monogram: string;
}) {
  const [phase, setPhase] = useState<"hidden" | "opening" | "leaving">(
    "hidden",
  );
  useEffect(() => {
    if (!enabled || (location.hash && location.hash !== "#home")) {
      setPhase("hidden");
      return;
    }
    const params = new URLSearchParams(location.search);
    if (params.get("intro") === "off") return;
    const key = "oryxen-react-intro-" + (claret ? "claret" : "atlas");
    try {
      if (sessionStorage.getItem(key) && params.get("intro") !== "1") return;
      sessionStorage.setItem(key, "1");
    } catch {
      /* opaque app surface */
    }
    let disposed = false;
    const timers: ReturnType<typeof setTimeout>[] = [];
    setPhase("opening");
    const minimum = new Promise((resolve) =>
      timers.push(setTimeout(resolve, 700)),
    );
    const cap = new Promise((resolve) =>
      timers.push(setTimeout(resolve, 2600)),
    );
    void Promise.race([Promise.all([document.fonts.ready, minimum]), cap]).then(
      () => {
        if (disposed) return;
        setPhase("leaving");
        timers.push(
          setTimeout(
            () => {
              if (!disposed) setPhase("hidden");
            },
            claret ? 950 : 600,
          ),
        );
      },
    );
    return () => {
      disposed = true;
      timers.forEach(clearTimeout);
    };
  }, [claret, enabled]);
  if (phase === "hidden") return null;
  return claret ? (
    <div className={`veil react-intro-${phase}`} aria-hidden="true">
      {monogram}
    </div>
  ) : (
    <div className={`atlas-loader react-intro-${phase}`} aria-hidden="true">
      <div className="loader-mark">{monogram}</div>
      <div className="loader-name">{name}</div>
      <div className="loader-bar">
        <i />
      </div>
    </div>
  );
}
