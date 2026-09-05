import "./home-hero-ecdc18c2.css";
import { useEffect } from "react";
import { contentValue } from "@/content/generated-content";
import { LocalImage, Reveal } from "@/components/generated/SharedSystems";
import { publicRouteUrl } from "@/app/ResourceUrl";

export default function HomeHero() {
  const primaryHref = contentValue("content:home:home:hero:primary-cta-href-6ce090b7");
  const secondaryHref = contentValue("content:home:home:hero:secondary-cta-href-70eecaa9");

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return undefined;
    const trigger = document.querySelector("#hero");
    const target = document.querySelector("#hero .hero-content");
    if (!trigger || !target) return undefined;
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        target.setAttribute("data-motion-ready", "true");
        observer.disconnect();
      }
    }, { threshold: 0.2 });
    observer.observe(trigger);
    return () => observer.disconnect();
  }, []);

  return (
    <section id="hero" data-content-id="home:hero" data-region-id="region:home:home:hero" className="home-hero">
      <div className="hero-atmosphere" data-resource-marker="home-hero-atmosphere">
        <LocalImage resourceId="assumed-image:home:hero:0" sizes="(max-width: 40rem) 100vw, 48vw" loading="eager" fit="cover" focalPosition="62% 48%" alt="" />
      </div>
      <Reveal className="hero-content" data-region-id="region:home:home:hero">
        <p className="hero-eyebrow">{contentValue("content:home:home:hero:eyebrow-0fe77a59")}</p>
        <h1>{contentValue("content:home:home:hero:headline-25b1ed96")}</h1>
        <p className="hero-body">{contentValue("content:home:home:hero:body-230d8358")}</p>
        <div className="hero-actions">
          <a className="hero-primary" href={publicRouteUrl("/") + primaryHref.replace(/^\//, "").replace(/^#/, "#")} data-approved-href={primaryHref} data-cta-kind={contentValue("content:home:home:hero:primary-cta-kind-dd5e7a62")}>{contentValue("content:home:home:hero:primary-cta-label-7207f029")}</a>
          <a className="hero-secondary" href={secondaryHref} data-approved-href={secondaryHref} data-cta-kind={contentValue("content:home:home:hero:secondary-cta-kind-28fba597")}>{contentValue("content:home:home:hero:secondary-cta-label-984108d8")}</a>
        </div>
      </Reveal>
    </section>
  );
}
