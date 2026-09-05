import { useEffect, useState } from "react";
import { RouteShell } from "../../components/generated/SharedSystems";
import HomeHero from "./sections/home-hero-ecdc18c2";
import HomeSelectedWork from "./sections/home-selected-work-2f0991ad";
import HomeApproach from "./sections/home-approach-db60527f";
import HomeExperience from "./sections/home-experience-40ccbde1";
import HomeDesignSystems from "./sections/home-design-systems-25820d29";
import HomeAboutConnect from "./sections/home-about-connect-618909a7";
import "./route.css";

const sectionIds = [
  "hero",
  "selected-work",
  "approach",
  "experience",
  "design-systems",
  "about-connect",
] as const;

export default function HomeRoute() {
  const [currentSection, setCurrentSection] = useState<(typeof sectionIds)[number]>("hero");

  useEffect(() => {
    const sections = sectionIds
      .map((sectionId) => document.getElementById(sectionId))
      .filter((section): section is HTMLElement => Boolean(section));
    if (typeof IntersectionObserver === "undefined" || sections.length === 0) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
        if (visible) setCurrentSection(visible.target.id as (typeof sectionIds)[number]);
      },
      { rootMargin: "-18% 0px -62% 0px", threshold: [0.1, 0.35, 0.6] },
    );

    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  return (
    <RouteShell
      routeId="home"
      routePath="/"
      navigation={
        <nav className="home-route-navigation" data-chapter-spine="true" data-current-section={currentSection} aria-label="Portfolio sections">
          <span className="home-route-navigation__marker" aria-hidden="true" />
          <a href="#hero" data-section-id="hero" data-current={currentSection === "hero" ? "true" : "false"} aria-current={currentSection === "hero" ? "location" : undefined}>Hero</a>
          <a href="#selected-work" data-section-id="selected-work" data-current={currentSection === "selected-work" ? "true" : "false"} aria-current={currentSection === "selected-work" ? "location" : undefined}>Selected Work</a>
          <a href="#approach" data-section-id="approach" data-current={currentSection === "approach" ? "true" : "false"} aria-current={currentSection === "approach" ? "location" : undefined}>Approach</a>
          <a href="#experience" data-section-id="experience" data-current={currentSection === "experience" ? "true" : "false"} aria-current={currentSection === "experience" ? "location" : undefined}>Experience</a>
          <a href="#design-systems" data-section-id="design-systems" data-current={currentSection === "design-systems" ? "true" : "false"} aria-current={currentSection === "design-systems" ? "location" : undefined}>Design Systems</a>
          <a href="#about-connect" data-section-id="about-connect" data-current={currentSection === "about-connect" ? "true" : "false"} aria-current={currentSection === "about-connect" ? "location" : undefined}>About Connect</a>
        </nav>
      }
    >
      {/* marker:criterion:home:hero */}
      <HomeHero />
      {/* marker:criterion:home:selected-work */}
      <HomeSelectedWork />
      {/* marker:criterion:home:approach */}
      <HomeApproach />
      {/* marker:criterion:home:experience */}
      <HomeExperience />
      {/* marker:criterion:home:design-systems */}
      <HomeDesignSystems />
      {/* marker:criterion:home:about-connect */}
      <HomeAboutConnect />
    </RouteShell>
  );
}
