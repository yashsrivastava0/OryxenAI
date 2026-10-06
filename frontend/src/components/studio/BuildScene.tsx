import { studioStageLabel, type StudioInFlightVM } from "../../data/adapters/studio";
import { GenerationEstimate } from "../GenerationEstimate";

const EVENTS = [
  { at: 0, name: "Story canvas", detail: "Setting the first frame" },
  { at: 5, name: "Opening section", detail: "Making room for your introduction" },
  { at: 11, name: "Selected work", detail: "Bringing the important details forward" },
  { at: 17, name: "Visual direction", detail: "Balancing type, color, and rhythm" },
  { at: 24, name: "Page view", detail: "Preparing a place to see it" },
];

const LINES = [
  "page / portfolio {",
  "  section / introduction {",
  "    story: the work that matters",
  "    focus: clear, considered, personal",
  "  }",
  "  section / selected work {",
  "    layout: room for the details",
  "    rhythm: space for each idea",
  "  }",
  "  section / contact {",
  "    invitation: start a conversation",
  "  }",
  "}",
];

export function BuildScene({ elapsedMs, inFlight, onStop }: { elapsedMs: number; inFlight: StudioInFlightVM | null; onStop?: () => Promise<void> }) {
  const seconds = Math.max(0, elapsedMs / 1000);
  const reducedMotion = typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  const visibleLines = reducedMotion ? LINES.length : Math.min(LINES.length, Math.floor(seconds / 2.1) + 1);
  const currentLineLength = reducedMotion ? Number.POSITIVE_INFINITY : Math.max(0, Math.floor((seconds % 2.1) * 24));
  const realStatus = inFlight ? studioStageLabel(inFlight.stage, inFlight.origin) : "Opening your verified preview";
  return (
    <section className="build-scene" aria-label="Portfolio build progress" aria-busy={Boolean(inFlight)}>
      <header className="build-scene__header">
        <div><p className="eyebrow">STUDIO / PAGE IN PROGRESS</p><h1>Your page is taking shape.</h1><p>Follow the visual story while your portfolio is built and checked.</p></div>
        <span className="build-scene__truth" role="status"><span className="pulse-indicator" aria-hidden="true" />{realStatus}</span>
      </header>
      <GenerationEstimate kind={inFlight?.origin === "change" ? "studio_edit" : "studio"} elapsedSeconds={elapsedMs / 1000} queued={inFlight?.stage === "queued"} />
      <div className="build-scene__body">
        <aside className="build-scene__activity" aria-label="Illustrative build activity">
          <div className="build-scene__aside-head"><strong>On the canvas</strong><span>Illustrative view</span></div>
          <div className="build-scene__events" aria-hidden="true">
            {EVENTS.filter((event) => reducedMotion || seconds >= event.at).map((event, index) => (
              <div className="build-scene__event" key={event.name} style={{ animationDelay: `${index * 60}ms` }}>
                <span className="build-scene__event-icon">{String(index + 1).padStart(2, "0")}</span>
                <span><strong>{event.name}</strong><small>{event.detail}</small></span>
              </div>
            ))}
          </div>
          <p className="build-scene__aside-note">The real page opens after the build is verified.</p>
        </aside>
        <div className="build-scene__editor" aria-hidden="true">
          <div className="build-scene__editor-bar"><span className="build-scene__window-dots"><i /><i /><i /></span><span>story.page</span><span>work.page</span><span>contact.page</span></div>
          <div className="build-scene__editor-layout">
            <div className="build-scene__code">
              {LINES.slice(0, visibleLines).map((line, index) => (
                <div className="build-scene__line" key={index}><span>{String(index + 1).padStart(2, "0")}</span><code>{index === visibleLines - 1 ? line.slice(0, currentLineLength) : line}</code>{index === visibleLines - 1 && <i className="build-scene__caret" />}</div>
              ))}
            </div>
            <div className="build-scene__canvas">
              <div className="build-scene__canvas-bar"><span>PAGE COMPOSITION</span><i /></div>
              <div className="build-scene__mock-hero"><small>INTRODUCTION</small><b /><b /><b /></div>
              <div className="build-scene__mock-grid"><span /><span /><span /></div>
              <div className="build-scene__mock-footer" />
            </div>
          </div>
        </div>
      </div>
      <footer className="build-scene__footer"><span>This illustration is a view of the process. Your actual preview appears when checks finish.{inFlight?.elapsedSeconds != null && <span className="build-scene__elapsed"> Elapsed: {Math.floor(inFlight.elapsedSeconds)}s</span>}</span>{inFlight && onStop && <button type="button" className="btn-quiet" onClick={() => void onStop()}>Stop building</button>}</footer>
    </section>
  );
}
