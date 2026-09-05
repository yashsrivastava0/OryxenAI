import "./home-approach-db60527f.css";
import { useEffect } from "react";
import { contentValue } from "@/content/generated-content";
import { LocalImage, StaggerGroup } from "@/components/generated/SharedSystems";

export default function HomeApproach() {
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return undefined;
    const trigger = document.querySelector("#approach .approach-steps");
    const target = document.querySelector("#approach .approach-steps");
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
    <section id="approach" data-content-id="home:approach" className="approach-section">
      <div className="approach-intro">
        <p className="section-label">{contentValue("content:home:home:approach:section-label-7cac7d3b")}</p>
        <h2>{contentValue("content:home:home:approach:headline-25b1ed96")}</h2>
      </div>
      <div className="approach-layout">
        <StaggerGroup className="approach-steps" data-region-id="region:home:home:approach">
          <article className="approach-step"><span className="step-number">01</span><div><h3>{contentValue("content:home:home:approach:steps-0-title-4c179739")}</h3><p>{contentValue("content:home:home:approach:steps-0-text-1890c1fe")}</p></div></article>
          <article className="approach-step"><span className="step-number">02</span><div><h3>{contentValue("content:home:home:approach:steps-1-title-185a920e")}</h3><p>{contentValue("content:home:home:approach:steps-1-text-8fcdd284")}</p></div></article>
          <article className="approach-step"><span className="step-number">03</span><div><h3>{contentValue("content:home:home:approach:steps-2-title-4d1eb8d4")}</h3><p>{contentValue("content:home:home:approach:steps-2-text-5e8739a6")}</p></div></article>
          <article className="approach-step"><span className="step-number">04</span><div><h3>{contentValue("content:home:home:approach:steps-3-title-a45dc319")}</h3><p>{contentValue("content:home:home:approach:steps-3-text-49106373")}</p></div></article>
        </StaggerGroup>
        <div className="approach-atmosphere" data-resource-marker="approach-process"><LocalImage resourceId="assumed-image:home:approach:3" sizes="(max-width: 40rem) 100vw, 38vw" loading="lazy" fit="cover" focalPosition="50% 45%" alt="" /></div>
      </div>
    </section>
  );
}
