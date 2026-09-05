import { RouteShell } from "../../components/generated/SharedSystems";
import HomeHero from "./sections/home-hero-ecdc18c2";
import HomeSelectedWork from "./sections/home-selected-work-2f0991ad";
import HomeApproach from "./sections/home-approach-db60527f";
import HomeExperience from "./sections/home-experience-40ccbde1";
import HomeDesignSystems from "./sections/home-design-systems-25820d29";
import HomeAboutConnect from "./sections/home-about-connect-618909a7";
import "./route.css";

export default function HomeRoute() {
  return (
    <RouteShell
      routeId="home"
      routePath="/"
      navigation={
        <nav className="route-navigation" aria-label="Portfolio sections">
          <a href="#hero">Hero</a>
          <a href="#selected-work">Selected Work</a>
          <a href="#approach">Approach</a>
          <a href="#experience">Experience</a>
          <a href="#design-systems">Design Systems</a>
          <a href="#about-connect">About Connect</a>
        </nav>
      }
    >
      {/* marker:criterion:home:hero */}
      {/* marker:criterion:home:selected-work */}
      {/* marker:criterion:home:approach */}
      {/* marker:criterion:home:experience */}
      {/* marker:criterion:home:design-systems */}
      {/* marker:criterion:home:about-connect */}
      <HomeHero />
      <HomeSelectedWork />
      <HomeApproach />
      <HomeExperience />
      <HomeDesignSystems />
      <HomeAboutConnect />
    </RouteShell>
  );
}
