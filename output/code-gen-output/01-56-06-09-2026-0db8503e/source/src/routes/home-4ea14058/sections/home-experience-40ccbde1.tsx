import "./home-experience-40ccbde1.css";
import { contentValue } from "../../../content/generated-content";

export default function HomeExperience() {
  return (
    <section id="experience" data-content-id="home:experience" data-region-id="region:home:home:experience" className="home-experience">
      <div className="home-experience__intro">
        <p className="home-experience__label">{contentValue("content:home:home:experience:section-label-7cac7d3b")}</p>
      </div>
      <div className="home-experience__timeline" aria-label="Experience">
        <article className="home-experience__role">
          <time className="home-experience__dates">{contentValue("content:home:home:experience:roles-0-dates-2fa94edc")}</time>
          <div className="home-experience__marker" aria-hidden="true" />
          <div className="home-experience__detail">
            <p className="home-experience__organization">{contentValue("content:home:home:experience:roles-0-organization-f347d8ba")}</p>
            <h2 className="home-experience__role-title">{contentValue("content:home:home:experience:roles-0-role-f356168e")}</h2>
            <p className="home-experience__summary">{contentValue("content:home:home:experience:roles-0-summary-40fc60bd")}</p>
          </div>
        </article>
        <article className="home-experience__role">
          <time className="home-experience__dates">{contentValue("content:home:home:experience:roles-1-dates-faeee3d2")}</time>
          <div className="home-experience__marker" aria-hidden="true" />
          <div className="home-experience__detail">
            <p className="home-experience__organization">{contentValue("content:home:home:experience:roles-1-organization-86f1f286")}</p>
            <h2 className="home-experience__role-title">{contentValue("content:home:home:experience:roles-1-role-c7dd7e5e")}</h2>
            <p className="home-experience__summary">{contentValue("content:home:home:experience:roles-1-summary-d21431ee")}</p>
          </div>
        </article>
      </div>
      <div className="home-experience__atmosphere" data-resource="experience-collaboration-atmosphere" aria-hidden="true" />
    </section>
  );
}
