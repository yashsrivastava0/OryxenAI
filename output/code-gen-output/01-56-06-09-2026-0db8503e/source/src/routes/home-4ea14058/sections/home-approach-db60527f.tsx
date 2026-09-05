import { contentValue } from "../../../content/generated-content";
import { LocalImage } from "../../../components/generated/SharedSystems";
import "./home-approach-db60527f.css";

export default function HomeApproach() {
  return (
    <section id="approach" data-content-id="home:approach" data-region-id="region:home:home:approach" className="home-approach">
      <div className="home-approach__heading"><p className="home-approach__label">{contentValue("content:home:home:approach:section-label-7cac7d3b")}</p><h2>{contentValue("content:home:home:approach:headline-25b1ed96")}</h2></div>
      <div className="home-approach__layout"><div className="home-approach__atmosphere" data-resource="approach-process-atmosphere"><LocalImage resourceId="assumed-image:home:approach:3" alt="" sizes="(max-width: 48rem) 100vw, 46vw" loading="lazy" fit="cover" focalPosition="50% 45%" /></div><ol className="home-approach__steps"><li><span className="home-approach__number">01</span><div><h3>{contentValue("content:home:home:approach:steps-0-title-4c179739")}</h3><p>{contentValue("content:home:home:approach:steps-0-text-1890c1fe")}</p></div></li><li><span className="home-approach__number">02</span><div><h3>{contentValue("content:home:home:approach:steps-1-title-185a920e")}</h3><p>{contentValue("content:home:home:approach:steps-1-text-8fcdd284")}</p></div></li><li><span className="home-approach__number">03</span><div><h3>{contentValue("content:home:home:approach:steps-2-title-4d1eb8d4")}</h3><p>{contentValue("content:home:home:approach:steps-2-text-5e8739a6")}</p></div></li><li><span className="home-approach__number">04</span><div><h3>{contentValue("content:home:home:approach:steps-3-title-a45dc319")}</h3><p>{contentValue("content:home:home:approach:steps-3-text-49106373")}</p></div></li></ol></div>
    </section>
  );
}
