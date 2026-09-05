import { contentValue } from "../../../content/generated-content";
import { LocalImage, Reveal } from "../../../components/generated/SharedSystems";
import { publicRouteUrl } from "../../../app/ResourceUrl";
import "./home-hero-ecdc18c2.css";

export default function HomeHero() {
  const primaryHref = contentValue("content:home:home:hero:primary-cta-href-6ce090b7");
  const secondaryHref = contentValue("content:home:home:hero:secondary-cta-href-70eecaa9");

  return (
    <section id="hero" data-content-id="home:hero" data-region-id="region:home:home:hero" className="home-hero">
      <div className="home-hero__frame">
        <Reveal data-motion-target="hero-entrance" className="home-hero__copy">
          <p className="home-hero__eyebrow">{contentValue("content:home:home:hero:eyebrow-0fe77a59")}</p>
          <h1>{contentValue("content:home:home:hero:headline-25b1ed96")}</h1>
          <p className="home-hero__body">{contentValue("content:home:home:hero:body-230d8358")}</p>
          <div className="home-hero__actions">
            <a className="home-hero__primary" href={publicRouteUrl("/") + primaryHref} data-cta-kind={contentValue("content:home:home:hero:primary-cta-kind-dd5e7a62")}>{contentValue("content:home:home:hero:primary-cta-label-7207f029")}</a>
            <a className="home-hero__secondary" href={secondaryHref} data-cta-kind={contentValue("content:home:home:hero:secondary-cta-kind-28fba597")} rel="noreferrer" target="_blank">{contentValue("content:home:home:hero:secondary-cta-label-984108d8")}</a>
          </div>
        </Reveal>
        <div className="home-hero__atmosphere" data-resource="home-hero-atmosphere"><LocalImage resourceId="assumed-image:home:hero:0" alt="" sizes="(max-width: 48rem) 100vw, 42vw" loading="eager" fit="cover" focalPosition="60% 45%" /></div>
      </div>
    </section>
  );
}
