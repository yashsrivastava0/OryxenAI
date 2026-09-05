import "./home-selected-work-2f0991ad.css";
import { contentValue } from "@/content/generated-content";
import { LocalImage } from "@/components/generated/SharedSystems";

export default function HomeSelectedWork() {
  return (
    <section id="selected-work" data-content-id="home:selected-work" className="selected-work-section">
      <div className="selected-work-heading">
        <p className="section-label">{contentValue("content:home:home:selected-work:section-label-7cac7d3b")}</p>
        <h2>{contentValue("content:home:home:selected-work:headline-25b1ed96")}</h2>
        <p>{contentValue("content:home:home:selected-work:intro-c432b372")}</p>
      </div>
      <div className="work-ledger" data-region-id="region:home:home:selected-work">
        <div className="project-list">
          <article className="project-entry"><div className="project-meta">{contentValue("content:home:home:selected-work:projects-0-domain-8dba42ff")}</div><h3>{contentValue("content:home:home:selected-work:projects-0-title-09ab233d")}</h3><p>{contentValue("content:home:home:selected-work:projects-0-description-b3e99743")}</p><p className="project-contribution">{contentValue("content:home:home:selected-work:projects-0-contribution-39627542")}</p></article>
          <article className="project-entry"><div className="project-meta">{contentValue("content:home:home:selected-work:projects-1-domain-25c4da4b")}</div><h3>{contentValue("content:home:home:selected-work:projects-1-title-b8f6542c")}</h3><p>{contentValue("content:home:home:selected-work:projects-1-description-64567fb7")}</p><p className="project-contribution">{contentValue("content:home:home:selected-work:projects-1-contribution-ccc18b2e")}</p></article>
          <article className="project-entry"><div className="project-meta">{contentValue("content:home:home:selected-work:projects-2-domain-7f9e2fa7")}</div><h3>{contentValue("content:home:home:selected-work:projects-2-title-e91dc165")}</h3><p>{contentValue("content:home:home:selected-work:projects-2-description-d138bf06")}</p><p className="project-contribution">{contentValue("content:home:home:selected-work:projects-2-contribution-2d016083")}</p></article>
          <article className="project-entry"><div className="project-meta">{contentValue("content:home:home:selected-work:projects-3-domain-ffb85e96")}</div><h3>{contentValue("content:home:home:selected-work:projects-3-title-2070585f")}</h3><p>{contentValue("content:home:home:selected-work:projects-3-description-7ce112c6")}</p><p className="project-contribution">{contentValue("content:home:home:selected-work:projects-3-contribution-180d035a")}</p></article>
        </div>
        <div className="work-atmosphere" data-resource-marker="selected-work-process"><LocalImage resourceId="assumed-image:home:selected-work:2" sizes="(max-width: 40rem) 100vw, 24vw" loading="lazy" fit="cover" focalPosition="50% 50%" alt="" /></div>
      </div>
    </section>
  );
}
