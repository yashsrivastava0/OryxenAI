import "./home-about-connect-618909a7.css";
import { LocalImage } from "../../../components/generated/SharedSystems";
import { contentValue } from "../../../content/generated-content";

export default function HomeAboutConnect() {
  return (
    <section id="about-connect" data-content-id="home:about-connect" data-region-id="region:home:home:about-connect" className="home-about-connect">
      <div className="home-about-connect__content">
        <p className="home-about-connect__label">{contentValue("content:home:home:about-connect:section-label-7cac7d3b")}</p>
        <h2>{contentValue("content:home:home:about-connect:headline-25b1ed96")}</h2>
        <p className="home-about-connect__body">{contentValue("content:home:home:about-connect:body-230d8358")}</p>
        <p className="home-about-connect__cta">{contentValue("content:home:home:about-connect:cta-061ab7e7")}</p>
        <nav className="home-about-connect__links" aria-label="Connect">
          <a data-kind={contentValue("content:home:home:about-connect:links-0-kind-4310e500")} href={contentValue("content:home:home:about-connect:links-0-href-9c859aa2")}>{contentValue("content:home:home:about-connect:links-0-label-1f19848d")}</a>
          <a data-kind={contentValue("content:home:home:about-connect:links-1-kind-a169d5bc")} href={contentValue("content:home:home:about-connect:links-1-href-0fdd6415")}>{contentValue("content:home:home:about-connect:links-1-label-65b26fe4")}</a>
          <a data-kind={contentValue("content:home:home:about-connect:links-2-kind-ce718cef")} href={contentValue("content:home:home:about-connect:links-2-href-2be7ac37")}>{contentValue("content:home:home:about-connect:links-2-label-1d3a7cf7")}</a>
        </nav>
      </div>
      <div className="home-about-connect__aside">
        <div className="home-about-connect__image" data-resource="about-learning-atmosphere">
          <LocalImage resourceId="assumed-image:home:about-connect:5" sizes="(max-width: 48rem) 100vw, 34vw" loading="lazy" fit="cover" focalPosition="50% 50%" alt="" />
        </div>
        <div className="home-about-connect__details">
          <p>{contentValue("content:home:home:about-connect:education-0-bc413744")}</p>
          <p>{contentValue("content:home:home:about-connect:education-1-bfd75c24")}</p>
          <p>{contentValue("content:home:home:about-connect:education-2-d4863154")}</p>
          <p>{contentValue("content:home:home:about-connect:education-3-cba49a3d")}</p>
          <p>{contentValue("content:home:home:about-connect:languages-0-206f6001")}</p>
          <p>{contentValue("content:home:home:about-connect:languages-1-a0d75f8c")}</p>
        </div>
      </div>
    </section>
  );
}
