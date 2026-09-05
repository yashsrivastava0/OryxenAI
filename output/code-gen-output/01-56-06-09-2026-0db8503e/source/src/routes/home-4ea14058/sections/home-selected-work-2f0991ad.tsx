import { contentValue } from "../../../content/generated-content";
import { LocalImage } from "../../../components/generated/SharedSystems";
import "./home-selected-work-2f0991ad.css";

export default function HomeSelectedWork() {
  return (
    <section id="selected-work" data-content-id="home:selected-work" data-region-id="region:home:home:selected-work" data-distinctive-move="move-home-selected-work-ledger" className="selected-work">
      <div className="selected-work__intro"><p className="selected-work__label">{contentValue("content:home:home:selected-work:section-label-7cac7d3b")}</p><h2>{contentValue("content:home:home:selected-work:headline-25b1ed96")}</h2><p>{contentValue("content:home:home:selected-work:intro-c432b372")}</p></div>
      <div className="selected-work__composition">
        <div className="selected-work__ledger">
          <article data-project-row className="selected-work__row"><span className="selected-work__index">01</span><div><p className="selected-work__domain">{contentValue("content:home:home:selected-work:projects-0-domain-8dba42ff")}</p><h3>{contentValue("content:home:home:selected-work:projects-0-title-09ab233d")}</h3></div><p>{contentValue("content:home:home:selected-work:projects-0-description-b3e99743")}</p><p className="selected-work__contribution">{contentValue("content:home:home:selected-work:projects-0-contribution-39627542")}</p></article>
          <article data-project-row className="selected-work__row"><span className="selected-work__index">02</span><div><p className="selected-work__domain">{contentValue("content:home:home:selected-work:projects-1-domain-25c4da4b")}</p><h3>{contentValue("content:home:home:selected-work:projects-1-title-b8f6542c")}</h3></div><p>{contentValue("content:home:home:selected-work:projects-1-description-64567fb7")}</p><p className="selected-work__contribution">{contentValue("content:home:home:selected-work:projects-1-contribution-ccc18b2e")}</p></article>
          <article data-project-row className="selected-work__row"><span className="selected-work__index">03</span><div><p className="selected-work__domain">{contentValue("content:home:home:selected-work:projects-2-domain-7f9e2fa7")}</p><h3>{contentValue("content:home:home:selected-work:projects-2-title-e91dc165")}</h3></div><p>{contentValue("content:home:home:selected-work:projects-2-description-d138bf06")}</p><p className="selected-work__contribution">{contentValue("content:home:home:selected-work:projects-2-contribution-2d016083")}</p></article>
          <article data-project-row className="selected-work__row"><span className="selected-work__index">04</span><div><p className="selected-work__domain">{contentValue("content:home:home:selected-work:projects-3-domain-ffb85e96")}</p><h3>{contentValue("content:home:home:selected-work:projects-3-title-2070585f")}</h3></div><p>{contentValue("content:home:home:selected-work:projects-3-description-7ce112c6")}</p><p className="selected-work__contribution">{contentValue("content:home:home:selected-work:projects-3-contribution-180d035a")}</p></article>
        </div>
        <div className="selected-work__texture" data-resource="selected-work-texture"><LocalImage resourceId="assumed-image:home:selected-work:2" alt="" sizes="(max-width: 48rem) 100vw, 24vw" loading="lazy" fit="cover" focalPosition="50% 50%" /></div>
      </div>
    </section>
  );
}
