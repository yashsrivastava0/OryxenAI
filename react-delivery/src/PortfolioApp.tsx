import { useEffect, useRef } from "react";
import { EditorialForest } from "./themes/EditorialForest";
import { CobaltClassic } from "./themes/CobaltClassic";
import { ObsidianSignal } from "./themes/ObsidianSignal";
import { CobaltAtlas } from "./themes/CobaltAtlas";
import { ClaretMarquee } from "./themes/ClaretMarquee";
import { InteractiveTheme } from "./interactive/InteractiveTheme";
import type { Portfolio } from "./template-values";

export const adapters = {
  "editorial-forest/v1": EditorialForest,
  "editorial-forest-motion/v1": EditorialForest,
  "cobalt-atlas/v1": CobaltClassic,
  "obsidian-signal/v1": ObsidianSignal,
  "cobalt-atlas/v2": CobaltAtlas,
  "claret-marquee/v1": ClaretMarquee,
};

export function PortfolioApp({ portfolio }: { portfolio: Portfolio }) {
  const host = useRef<HTMLDivElement>(null);
  const Adapter = adapters[portfolio.theme_id as keyof typeof adapters];
  useEffect(() => {
    const previous = {
      title: document.title,
      lang: document.documentElement.lang,
      body: document.body.className,
    };
    document.title = portfolio.c.metadata.title;
    document.documentElement.lang = portfolio.lang;
    document.body.className = portfolio.body_class;
    return () => {
      document.title = previous.title;
      document.documentElement.lang = previous.lang;
      document.body.className = previous.body;
    };
  }, [portfolio]);
  if (!Adapter) throw new Error("This React theme revision is unsupported.");
  const content = <Adapter c={portfolio.c} d={portfolio.d} />;
  return (
    <div ref={host} className="react-portfolio">
      {portfolio.theme_id === "cobalt-atlas/v2" ||
      portfolio.theme_id === "claret-marquee/v1" ? (
        <InteractiveTheme portfolio={portfolio} host={host}>
          {content}
        </InteractiveTheme>
      ) : (
        content
      )}
    </div>
  );
}
