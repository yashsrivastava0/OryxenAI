// Migrated from the immutable host template; interactions are implemented in React.
import { Fragment } from "react";
import {
  truthy,
  range,
  ProjectLink,
  type TemplateValues,
} from "../template-values";
import {
  RouteView,
  PortfolioLink,
  PortfolioNav,
  CaseContents,
} from "../interactive/routing";
import { ThemeElement, Dust } from "../interactive/motion";
export function CobaltAtlas({ c, d }: TemplateValues) {
  return (
    <>
      <PortfolioLink className={"skip-link"} href={"#main"}>
        {"Skip to content"}
      </PortfolioLink>
      {"\n"}
      <div className={"scroll-progress"} aria-hidden={"true"}></div>
      {"\n"}
      <header className={"site-header"}>
        {"\n  "}
        <PortfolioLink
          className={"wordmark"}
          href={"#home"}
          aria-label={d.home_label}
        >
          <span className={"wordmark-mark"}>
            {d.monogram}
            <span className={"wordmark-dot"}>{"."}</span>
          </span>
          <span className={"wordmark-name"} data-field={"hero.name"}>
            {c.hero.name}
          </span>
        </PortfolioLink>
        {"\n  "}
        <PortfolioNav className={"site-nav"} aria-label={"Main navigation"}>
          <PortfolioLink href={"#home"}>{"Home"}</PortfolioLink>
          <PortfolioLink href={"#work"}>{"Work"}</PortfolioLink>
          <PortfolioLink href={"#about"}>{"About"}</PortfolioLink>
          <PortfolioLink href={"#contact"}>{"Contact"}</PortfolioLink>
        </PortfolioNav>
        {"\n  "}
        <PortfolioLink className={"header-cta"} href={"#contact"}>
          {"Let's talk "}
          <span aria-hidden={"true"}>{"↗"}</span>
        </PortfolioLink>
        {"\n"}
      </header>
      {"\n"}
      <main id={"main"}>
        {"\n"}
        <RouteView
          className={"route-view"}
          id={"home"}
          data-view={""}
          data-title={c.metadata.title}
        >
          {"\n  "}
          <section
            className={"hero section-pad"}
            aria-labelledby={"hero-title"}
          >
            {"\n    "}
            <div className={"hero-copy"}>
              <p className={"eyebrow"} data-field={"hero.eyebrow_primary"}>
                {c.hero.eyebrow_primary}
              </p>
              <ThemeElement as="h1" id={"hero-title"}>
                <span data-field={"hero.headline_prefix"}>
                  {c.hero.headline_prefix}
                </span>{" "}
                <em data-field={"hero.headline_emphasis"}>
                  {c.hero.headline_emphasis}
                </em>
              </ThemeElement>
              <ThemeElement
                as="p"
                className={"hero-lede"}
                data-field={"hero.intro"}
              >
                {c.hero.intro}
              </ThemeElement>
              <div className={"hero-actions"}>
                <PortfolioLink
                  className={"button button-primary"}
                  href={"#work"}
                >
                  {"Explore selected work "}
                  <span aria-hidden={"true"}>{"↗"}</span>
                </PortfolioLink>
                <PortfolioLink className={"text-link"} href={"#about"}>
                  {"Get to know me "}
                  <span aria-hidden={"true"}>{"↗"}</span>
                </PortfolioLink>
              </div>
              <div className={"hero-foot"}>
                <span>{"01 / Introduction"}</span>
                {truthy(c.hero.location) ? (
                  <>
                    <span data-field={"hero.location"}>{c.hero.location}</span>
                  </>
                ) : null}
              </div>
            </div>
            {"\n    "}
            <div className={"hero-visual"}>
              <div className={"hero-core"}>
                <span data-field={"hero.name"}>{c.hero.name}</span>
                <span className={"core-arrow"} aria-hidden={"true"}>
                  {"↗"}
                </span>
              </div>
              <div className={"hero-float hero-float-top"}>
                <span className={"mini-symbol"} aria-hidden={"true"}>
                  {"✳"}
                </span>
                <span data-field={"hero.eyebrow_secondary"}>
                  {c.hero.eyebrow_secondary}
                </span>
              </div>
              <p className={"visual-caption"}>
                <span>{"Fig. 01"}</span>
                <span>{"Abstract artwork"}</span>
              </p>
            </div>
            {"\n  "}
          </section>
          {"\n  "}
          {truthy(c.marquee_keywords) ? (
            <>
              <ThemeElement
                as="div"
                className={"marquee"}
                role={"region"}
                aria-label={"Areas of practice"}
              >
                <ThemeElement as="ul" className={"marquee-track"}>
                  {c.marquee_keywords.map(
                    (keyword: any, index: number, items: any[]) => {
                      const loop = {
                        index0: index,
                        index: index + 1,
                        last: index === items.length - 1,
                        first: index === 0,
                      };
                      return (
                        <Fragment key={index}>
                          <li
                            data-field={
                              "" + "marquee_keywords[" + loop.index0 + "]"
                            }
                          >
                            {keyword}
                          </li>
                        </Fragment>
                      );
                    },
                  )}
                </ThemeElement>
              </ThemeElement>
            </>
          ) : null}
          {"\n  "}
          <ThemeElement
            as="section"
            className={"intro-band section-pad atlas-appear"}
          >
            <p className={"section-kicker"}>{"The through line"}</p>
            <p
              className={"intro-statement"}
              data-field={"systems_practice.heading"}
            >
              {c.systems_practice.heading}
            </p>
            <div className={"intro-side"}>
              <span className={"asterisk"} aria-hidden={"true"}>
                {"✳"}
              </span>
              <p data-field={"systems_practice.intro"}>
                {c.systems_practice.intro}
              </p>
            </div>
          </ThemeElement>
          {"\n  "}
          <section
            className={"work-section section-pad"}
            id={"work"}
            aria-labelledby={"work-title"}
          >
            <ThemeElement as="div" className={"section-heading atlas-appear"}>
              <div>
                <p className={"section-kicker"}>{"01 / Selected work"}</p>
                <ThemeElement as="h2" id={"work-title"}>
                  {"Selected "}
                  <em>{"work."}</em>
                </ThemeElement>
              </div>
              <p>{"Projects and ideas shaped by this portfolio."}</p>
            </ThemeElement>
            {"\n    "}
            {truthy(c.atlas.projects) ? (
              <>
                <div className={"project-list"}>
                  {c.atlas.projects.map(
                    (project: any, index: number, items: any[]) => {
                      const loop = {
                        index0: index,
                        index: index + 1,
                        last: index === items.length - 1,
                        first: index === 0,
                      };
                      return (
                        <Fragment key={index}>
                          {"\n      "}
                          {(() => {
                            const isCase = truthy(project.problem)
                              ? project.approach
                              : project.problem;
                            return (
                              <>
                                {"\n      "}
                                <ProjectLink
                                  className={"project-card atlas-appear"}
                                  project={project}
                                  index={loop.index}
                                >
                                  {"\n      "}
                                  <div
                                    className={"project-art"}
                                    data-art={d.arts[loop.index0]}
                                    data-tone={(loop.index0 % 4) + 1}
                                    aria-hidden={"true"}
                                  >
                                    <span className={"art-corner"}>
                                      {"0"}
                                      {loop.index}
                                      {" / "}
                                      {truthy(
                                        project.kind === "illustrative",
                                      ) ? (
                                        <>{"Illustrative concept"}</>
                                      ) : (
                                        <>{"Selected project"}</>
                                      )}
                                    </span>
                                    <span className={"art-bottom"}>
                                      {project.title}
                                    </span>
                                  </div>
                                  {"\n      "}
                                  <div className={"project-info"}>
                                    <span className={"project-number"}>
                                      {"0"}
                                      {loop.index}
                                      {" — "}
                                      {truthy(
                                        project.kind === "illustrative",
                                      ) ? (
                                        <>
                                          {
                                            "Illustrative concept — not real client work"
                                          }
                                        </>
                                      ) : (
                                        <>{"Project"}</>
                                      )}
                                    </span>
                                    <div>
                                      <h3
                                        data-field={
                                          "" +
                                          "atlas.projects[" +
                                          loop.index0 +
                                          "].title"
                                        }
                                      >
                                        {project.title}
                                      </h3>
                                      <p
                                        data-field={
                                          "" +
                                          "atlas.projects[" +
                                          loop.index0 +
                                          "].summary"
                                        }
                                      >
                                        {project.summary}
                                      </p>
                                    </div>
                                    <span
                                      className={"project-arrow"}
                                      aria-hidden={"true"}
                                    >
                                      {"↗"}
                                    </span>
                                    {truthy(project.period) ? (
                                      <>
                                        <span
                                          className={"project-meta"}
                                          data-field={
                                            "" +
                                            "atlas.projects[" +
                                            loop.index0 +
                                            "].period"
                                          }
                                        >
                                          {project.period}
                                        </span>
                                      </>
                                    ) : null}
                                  </div>
                                  {"\n      "}
                                </ProjectLink>
                                {"\n    "}
                              </>
                            );
                          })()}
                        </Fragment>
                      );
                    },
                  )}
                </div>
              </>
            ) : (
              <>
                <ThemeElement as="div" className={"work-empty atlas-appear"}>
                  <div
                    className={"project-art"}
                    data-art={"orbit"}
                    data-tone={"1"}
                    aria-hidden={"true"}
                  ></div>
                  <div>
                    <p className={"section-kicker"}>{"Work in progress"}</p>
                    <h3>{"Your story can grow here."}</h3>
                    <p>
                      {"Project details can be added whenever you're ready."}
                    </p>
                  </div>
                </ThemeElement>
              </>
            )}
            {"\n  "}
          </section>
          {"\n  "}
          {truthy(c.atlas.statistics) ? (
            <>
              <ThemeElement
                as="section"
                className={"impact-section section-pad atlas-appear"}
              >
                <div className={"impact-head"}>
                  <p className={"section-kicker"}>{"02 / Measured moments"}</p>
                  <ThemeElement as="h2">
                    {"Selected "}
                    <em>{"results."}</em>
                  </ThemeElement>
                  {truthy(d.sample.statistics) ? (
                    <>
                      <p className={"project-meta"}>
                        {"Sample content — replace with your own details."}
                      </p>
                    </>
                  ) : null}
                </div>
                <div className={"impact-grid"}>
                  {c.atlas.statistics.map(
                    (stat: any, index: number, items: any[]) => {
                      const loop = {
                        index0: index,
                        index: index + 1,
                        last: index === items.length - 1,
                        first: index === 0,
                      };
                      return (
                        <Fragment key={index}>
                          <div>
                            <ThemeElement
                              as="strong"
                              data-field={
                                "" +
                                "atlas.statistics[" +
                                loop.index0 +
                                "].value"
                              }
                            >
                              {stat.value}
                            </ThemeElement>
                            <p
                              data-field={
                                "" +
                                "atlas.statistics[" +
                                loop.index0 +
                                "].label"
                              }
                            >
                              {stat.label}
                            </p>
                          </div>
                        </Fragment>
                      );
                    },
                  )}
                </div>
              </ThemeElement>
            </>
          ) : null}
          {"\n  "}
          <ThemeElement
            as="section"
            className={"approach-section section-pad atlas-appear"}
          >
            <div>
              <p className={"section-kicker"}>{"03 / How I work"}</p>
              <ThemeElement as="h2">
                {"Ways of "}
                <em>{"working."}</em>
              </ThemeElement>
            </div>
            <div className={"approach-list"}>
              {c.systems_practice.pillars.map(
                (pillar: any, index: number, items: any[]) => {
                  const loop = {
                    index0: index,
                    index: index + 1,
                    last: index === items.length - 1,
                    first: index === 0,
                  };
                  return (
                    <Fragment key={index}>
                      <div>
                        <span>
                          {"0"}
                          {loop.index}
                        </span>
                        <h3
                          data-field={
                            "" +
                            "systems_practice.pillars[" +
                            loop.index0 +
                            "].title"
                          }
                        >
                          {pillar.title}
                        </h3>
                        <p
                          data-field={
                            "" +
                            "systems_practice.pillars[" +
                            loop.index0 +
                            "].description"
                          }
                        >
                          {pillar.description}
                        </p>
                      </div>
                    </Fragment>
                  );
                },
              )}
            </div>
          </ThemeElement>
          {"\n  "}
          <section className={"contact-section section-pad"} id={"contact"}>
            <p className={"section-kicker"}>{"04 / Let's connect"}</p>
            <div className={"contact-grid"}>
              <ThemeElement as="h2" data-field={"connect.heading"}>
                {c.connect.heading}
              </ThemeElement>
              <div>
                <p data-field={"connect.intro"}>{c.connect.intro}</p>
                {c.connect.destinations.map(
                  (destination: any, index: number, items: any[]) => {
                    const loop = {
                      index0: index,
                      index: index + 1,
                      last: index === items.length - 1,
                      first: index === 0,
                    };
                    return (
                      <Fragment key={index}>
                        <PortfolioLink
                          className={"button button-light"}
                          href={destination.url}
                          {...(truthy(destination.url.startsWith("http"))
                            ? { target: "_blank", rel: "noopener noreferrer" }
                            : {})}
                        >
                          <span
                            data-field={
                              "" +
                              "connect.destinations[" +
                              loop.index0 +
                              "].label"
                            }
                          >
                            {destination.label}
                          </span>{" "}
                          <span aria-hidden={"true"}>{"↗"}</span>
                        </PortfolioLink>
                      </Fragment>
                    );
                  },
                )}
              </div>
            </div>
          </section>
          {"\n"}
        </RouteView>
        {"\n"}
        <RouteView
          className={"route-view inner-page"}
          id={"about"}
          data-view={""}
          data-title={"" + "About — " + c.hero.name}
        >
          {"\n  "}
          <section className={"page-hero section-pad"}>
            <p className={"section-kicker"}>{"02 / About"}</p>
            <div className={"page-hero-grid"}>
              <ThemeElement as="h1" data-field={"atlas.about_heading"}>
                {c.atlas.about_heading}
              </ThemeElement>
              <div>
                <figure
                  className={"portrait"}
                  data-initials={d.monogram}
                ></figure>
                <ThemeElement
                  as="p"
                  className={"page-lede"}
                  data-field={"atlas.about_intro"}
                >
                  {c.atlas.about_intro}
                </ThemeElement>
                <PortfolioLink className={"text-link"} href={"#contact"}>
                  {"Get in touch "}
                  <span aria-hidden={"true"}>{"↗"}</span>
                </PortfolioLink>
              </div>
            </div>
          </section>
          {"\n  "}
          {truthy(c.atlas.about_quote) ? (
            <>
              <ThemeElement
                as="section"
                className={"about-quote section-pad atlas-appear"}
              >
                <span className={"asterisk"} aria-hidden={"true"}>
                  {"✳"}
                </span>
                <blockquote data-field={"atlas.about_quote"}>
                  {c.atlas.about_quote}
                </blockquote>
              </ThemeElement>
            </>
          ) : null}
          {"\n  "}
          {truthy(c.atlas.experience) ? (
            <>
              <section className={"experience section-pad"}>
                <div className={"section-heading"}>
                  <div>
                    <p className={"section-kicker"}>{"01 / Journey"}</p>
                    <ThemeElement as="h2">{"Experience."}</ThemeElement>
                    {truthy(d.sample.experience) ? (
                      <>
                        <p className={"project-meta"}>
                          {"Sample content — replace with your own details."}
                        </p>
                      </>
                    ) : null}
                  </div>
                </div>
                <div className={"timeline"}>
                  {c.atlas.experience.map(
                    (row: any, index: number, items: any[]) => {
                      const loop = {
                        index0: index,
                        index: index + 1,
                        last: index === items.length - 1,
                        first: index === 0,
                      };
                      return (
                        <Fragment key={index}>
                          <ThemeElement
                            as="div"
                            className={"timeline-row atlas-appear"}
                          >
                            <span
                              data-field={
                                "" +
                                "atlas.experience[" +
                                loop.index0 +
                                "].dates"
                              }
                            >
                              {row.dates}
                            </span>
                            <div>
                              <h3
                                data-field={
                                  "" +
                                  "atlas.experience[" +
                                  loop.index0 +
                                  "].role"
                                }
                              >
                                {row.role}
                              </h3>
                              <p
                                data-field={
                                  "" +
                                  "atlas.experience[" +
                                  loop.index0 +
                                  "].organization"
                                }
                              >
                                {row.organization}
                              </p>
                              <p
                                data-field={
                                  "" +
                                  "atlas.experience[" +
                                  loop.index0 +
                                  "].description"
                                }
                              >
                                {row.description}
                              </p>
                            </div>
                            <b aria-hidden={"true"}>
                              {"0"}
                              {loop.index}
                            </b>
                          </ThemeElement>
                        </Fragment>
                      );
                    },
                  )}
                </div>
              </section>
            </>
          ) : null}
          {"\n  "}
          <ThemeElement
            as="section"
            className={"capabilities section-pad atlas-appear"}
          >
            <div>
              <p className={"section-kicker"}>{"02 / Practice"}</p>
              <ThemeElement
                as="h2"
                data-field={"technical_capabilities.heading"}
              >
                {c.technical_capabilities.heading}
              </ThemeElement>
            </div>
            <div className={"capability-grid"}>
              {c.technical_capabilities.groups.map(
                (group: any, index: number, items: any[]) => {
                  const loop = {
                    index0: index,
                    index: index + 1,
                    last: index === items.length - 1,
                    first: index === 0,
                  };
                  return (
                    <Fragment key={index}>
                      <div>
                        <span>
                          {"0"}
                          {loop.index}
                        </span>
                        <h3
                          data-field={
                            "" +
                            "technical_capabilities.groups[" +
                            loop.index0 +
                            "].heading"
                          }
                        >
                          {group.heading}
                        </h3>
                        <p>{group["items"].join(" · ")}</p>
                      </div>
                    </Fragment>
                  );
                },
              )}
            </div>
          </ThemeElement>
          {"\n  "}
          {truthy(c.atlas.education) ? (
            <>
              <ThemeElement
                as="section"
                className={"education section-pad atlas-appear"}
              >
                <div>
                  <p className={"section-kicker"}>{"03 / Foundation"}</p>
                  <ThemeElement as="h2">{"Education."}</ThemeElement>
                  {truthy(d.sample.education) ? (
                    <>
                      <p className={"project-meta"}>
                        {"Sample content — replace with your own details."}
                      </p>
                    </>
                  ) : null}
                </div>
                <div>
                  {c.atlas.education.map(
                    (row: any, index: number, items: any[]) => {
                      const loop = {
                        index0: index,
                        index: index + 1,
                        last: index === items.length - 1,
                        first: index === 0,
                      };
                      return (
                        <Fragment key={index}>
                          <div className={"education-row"}>
                            <ThemeElement
                              as="strong"
                              data-field={
                                "" +
                                "atlas.education[" +
                                loop.index0 +
                                "].credential"
                              }
                            >
                              {row.credential}
                            </ThemeElement>
                            <span
                              data-field={
                                "" +
                                "atlas.education[" +
                                loop.index0 +
                                "].institution"
                              }
                            >
                              {row.institution}
                            </span>
                            <span
                              data-field={
                                "" +
                                "atlas.education[" +
                                loop.index0 +
                                "].dates"
                              }
                            >
                              {row.dates}
                            </span>
                          </div>
                        </Fragment>
                      );
                    },
                  )}
                </div>
              </ThemeElement>
            </>
          ) : null}
          {"\n  "}
          <section className={"page-next section-pad"}>
            <p className={"section-kicker"}>{"Next / Selected work"}</p>
            <PortfolioLink href={"#work"}>
              {"See the work "}
              <span aria-hidden={"true"}>{"↗"}</span>
            </PortfolioLink>
          </section>
          {"\n"}
        </RouteView>
        {"\n"}
        {c.atlas.projects.map((project: any, index: number, items: any[]) => {
          const loop = {
            index0: index,
            index: index + 1,
            last: index === items.length - 1,
            first: index === 0,
          };
          return (
            <Fragment key={index}>
              {truthy(
                truthy(project.problem) ? project.approach : project.problem,
              ) ? (
                <>
                  {"\n"}
                  <RouteView
                    className={"route-view inner-page case-page"}
                    id={"" + "case-" + loop.index}
                    data-view={""}
                    data-title={"" + project.title + " — " + c.hero.name}
                  >
                    <section className={"case-hero section-pad"}>
                      <PortfolioLink className={"back-link"} href={"#work"}>
                        {"← All work"}
                      </PortfolioLink>
                      <p className={"section-kicker"}>
                        {"Case 0"}
                        {loop.index}
                        {truthy(project.kind === "illustrative") ? (
                          <>
                            {" / Illustrative concept — not real client work"}
                          </>
                        ) : null}
                      </p>
                      <ThemeElement
                        as="h1"
                        data-field={
                          "" + "atlas.projects[" + loop.index0 + "].title"
                        }
                      >
                        {project.title}
                      </ThemeElement>
                      <div className={"case-intro"}>
                        <p
                          data-field={
                            "" + "atlas.projects[" + loop.index0 + "].summary"
                          }
                        >
                          {project.summary}
                        </p>
                        {truthy(project.role) ? (
                          <>
                            <dl>
                              <div>
                                <dt>{"Role"}</dt>
                                <dd
                                  data-field={
                                    "" +
                                    "atlas.projects[" +
                                    loop.index0 +
                                    "].role"
                                  }
                                >
                                  {project.role}
                                </dd>
                              </div>
                            </dl>
                          </>
                        ) : null}
                      </div>
                    </section>
                    <section className={"case-art-section section-pad"}>
                      <div
                        className={"case-art-frame"}
                        data-art={d.arts[loop.index0]}
                        data-tone={(loop.index0 % 4) + 1}
                        role={"img"}
                        aria-label={"Abstract artwork"}
                      >
                        <span className={"art-corner"}>
                          {"0"}
                          {loop.index}
                          {" / Conceptual artwork"}
                        </span>
                      </div>
                      <p className={"visual-note"}>
                        {
                          "Conceptual artwork — illustrative, not a product screenshot."
                        }
                      </p>
                    </section>
                    <CaseContents
                      index={loop.index}
                      outcome={truthy(project.outcome)}
                    />
                    <section className={"case-body section-pad"}>
                      <ThemeElement
                        as="div"
                        id={`case-${loop.index}--s1`}
                        className={"case-text atlas-appear"}
                      >
                        <span>{"01 / The opportunity"}</span>
                        <ThemeElement as="h2">{"Problem"}</ThemeElement>
                        <p
                          data-field={
                            "" + "atlas.projects[" + loop.index0 + "].problem"
                          }
                        >
                          {project.problem}
                        </p>
                      </ThemeElement>
                      <ThemeElement
                        as="div"
                        id={`case-${loop.index}--s2`}
                        className={"case-text atlas-appear"}
                      >
                        <span>{"02 / The approach"}</span>
                        <ThemeElement as="h2">{"Approach"}</ThemeElement>
                        <p
                          data-field={
                            "" + "atlas.projects[" + loop.index0 + "].approach"
                          }
                        >
                          {project.approach}
                        </p>
                      </ThemeElement>
                      {truthy(project.outcome) ? (
                        <>
                          <ThemeElement
                            as="div"
                            id={`case-${loop.index}--s3`}
                            className={"case-result atlas-appear"}
                          >
                            <span>{"03 / Outcome"}</span>
                            <p
                              data-field={
                                "" +
                                "atlas.projects[" +
                                loop.index0 +
                                "].outcome"
                              }
                            >
                              {project.outcome}
                            </p>
                          </ThemeElement>
                        </>
                      ) : null}
                    </section>
                    <section className={"page-next section-pad"}>
                      <p className={"section-kicker"}>
                        {"Back / Selected work"}
                      </p>
                      <PortfolioLink href={"#work"}>
                        {"Explore all work "}
                        <span aria-hidden={"true"}>{"↗"}</span>
                      </PortfolioLink>
                    </section>
                  </RouteView>
                  {"\n"}
                </>
              ) : null}
            </Fragment>
          );
        })}
        {"\n"}
      </main>
      {"\n"}
      <footer className={"site-footer section-pad"}>
        <div>
          <PortfolioLink className={"footer-mark"} href={"#home"}>
            {d.monogram}
            <span>{"."}</span>
          </PortfolioLink>
          <p data-field={"hero.name"}>{c.hero.name}</p>
        </div>
        <div className={"footer-links"}>
          <PortfolioLink href={"#work"}>{"Work"}</PortfolioLink>
          <PortfolioLink href={"#about"}>{"About"}</PortfolioLink>
          <PortfolioLink href={"#contact"}>{"Contact"}</PortfolioLink>
        </div>
        <span className={"footer-top"}>
          <PortfolioLink href={"#home"}>{"Back to top ↑"}</PortfolioLink>
        </span>
      </footer>
      {"\n"}
      <span
        className={"sr-only"}
        id={"route-announcer"}
        role={"status"}
        aria-live={"polite"}
      ></span>
      {"\n"}
    </>
  );
}
