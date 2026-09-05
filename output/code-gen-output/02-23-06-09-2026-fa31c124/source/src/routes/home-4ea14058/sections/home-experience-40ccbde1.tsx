import { contentValue } from "../../../content/generated-content";
import { LocalImage } from "../../../components/generated/SharedSystems";
import "./home-experience-40ccbde1.css";

export default function HomeExperience() {
  return (
    <section id="experience" data-route-id="home" data-content-id="home:experience" className="experience-section">
      <div className="experience-shell">
        <p className="section-label">{contentValue("content:home:home:experience:section-label-7cac7d3b")}</p>
        <div className="experience-layout">
          <div className="experience-intro">
            <span className="experience-index">02</span>
            <p className="experience-note">Professional context</p>
          </div>
          <ol className="experience-timeline">
            <li className="experience-role">
              <time>{contentValue("content:home:home:experience:roles-0-dates-2fa94edc")}</time>
              <div>
                <p className="experience-organization">{contentValue("content:home:home:experience:roles-0-organization-f347d8ba")}</p>
                <h2>{contentValue("content:home:home:experience:roles-0-role-f356168e")}</h2>
                <p>{contentValue("content:home:home:experience:roles-0-summary-40fc60bd")}</p>
              </div>
            </li>
            <li className="experience-role">
              <time>{contentValue("content:home:home:experience:roles-1-dates-faeee3d2")}</time>
              <div>
                <p className="experience-organization">{contentValue("content:home:home:experience:roles-1-organization-86f1f286")}</p>
                <h2>{contentValue("content:home:home:experience:roles-1-role-c7dd7e5e")}</h2>
                <p>{contentValue("content:home:home:experience:roles-1-summary-d21431ee")}</p>
              </div>
            </li>
          </ol>
          <div className="experience-atmosphere" data-resource-marker="experience-collaboration" aria-hidden="true">
            <div className="experience-atmosphere-mark">/</div>
            <LocalImage resourceId="assumed-image:home:experience:1" alt="" sizes="(max-width: 40rem) 100vw, 30vw" loading="lazy" fit="cover" focalPosition="52% 48%" />
          </div>
        </div>
      </div>
    </section>
  );
}
