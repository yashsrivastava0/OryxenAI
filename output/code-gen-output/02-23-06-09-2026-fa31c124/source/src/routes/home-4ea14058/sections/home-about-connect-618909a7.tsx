import { contentValue } from "../../../content/generated-content";
import { LocalImage } from "../../../components/generated/SharedSystems";
import { publicRouteUrl } from "../../../app/ResourceUrl";
import "./home-about-connect-618909a7.css";

export default function HomeAboutConnect() {
  return (
    <section id="about-connect" data-route-id="home" data-content-id="home:about-connect" data-region-id="region:home:home:about-connect" className="about-section">
      <div className="about-shell">
        <p className="section-label">{contentValue("content:home:home:about-connect:section-label-7cac7d3b")}</p>
        <div className="about-layout">
          <div className="about-learning" data-resource-marker="about-learning" aria-hidden="true"><LocalImage resourceId="assumed-image:home:about-connect:5" alt="" sizes="(max-width: 40rem) 100vw, 30vw" loading="lazy" fit="cover" focalPosition="50% 50%" /></div>
          <div className="contact-path">
            <h2>{contentValue("content:home:home:about-connect:headline-25b1ed96")}</h2>
            <p className="about-body">{contentValue("content:home:home:about-connect:body-230d8358")}</p>
            <p className="about-cta">{contentValue("content:home:home:about-connect:cta-061ab7e7")}</p>
            <nav className="about-links" aria-label="Connect">
              <a data-content-kind={contentValue("content:home:home:about-connect:links-0-kind-4310e500")} href={contentValue("content:home:home:about-connect:links-0-href-9c859aa2")}>{contentValue("content:home:home:about-connect:links-0-label-1f19848d")}</a>
              <a data-content-kind={contentValue("content:home:home:about-connect:links-1-kind-a169d5bc")} href={contentValue("content:home:home:about-connect:links-1-href-0fdd6415")}>{contentValue("content:home:home:about-connect:links-1-label-65b26fe4")}</a>
              <a data-content-kind={contentValue("content:home:home:about-connect:links-2-kind-ce718cef")} href={contentValue("content:home:home:about-connect:links-2-href-2be7ac37")}>{contentValue("content:home:home:about-connect:links-2-label-1d3a7cf7")}</a>
            </nav>
            <div className="about-details"><div><p className="details-label">Education</p><ul><li>{contentValue("content:home:home:about-connect:education-0-bc413744")}</li><li>{contentValue("content:home:home:about-connect:education-1-bfd75c24")}</li><li>{contentValue("content:home:home:about-connect:education-2-d4863154")}</li><li>{contentValue("content:home:home:about-connect:education-3-cba49a3d")}</li></ul></div><div><p className="details-label">Languages</p><ul><li>{contentValue("content:home:home:about-connect:languages-0-206f6001")}</li><li>{contentValue("content:home:home:about-connect:languages-1-a0d75f8c")}</li></ul></div></div>
          </div>
        </div>
      </div>
    </section>
  );
}
