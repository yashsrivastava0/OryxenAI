// Migrated from the immutable host template; interactions are implemented in React.
import { Fragment } from "react";
import {
  truthy,
  range,
  ProjectLink,
  type TemplateValues,
} from "../template-values";
import { RouteView, PortfolioLink, PortfolioNav } from "../interactive/routing";
import { ThemeElement, Dust } from "../interactive/motion";
export function ClaretMarquee({ c, d }: TemplateValues) {
  return (
    <>
      {(() => {
        const hero = c.hero;
        return (
          <>
            {"\n"}
            {(() => {
              const atlas = c.atlas;
              return (
                <>
                  {"\n"}
                  {(() => {
                    const practice = c.systems_practice;
                    return (
                      <>
                        {"\n"}
                        {(() => {
                          const caps = c.technical_capabilities;
                          return (
                            <>
                              {"\n"}
                              {(() => {
                                const context = c.professional_context ?? {};
                                return (
                                  <>
                                    {"\n"}
                                    {(() => {
                                      const organizations =
                                        context.organizations ?? [];
                                      return (
                                        <>
                                          {"\n"}
                                          {(() => {
                                            const connect = c.connect;
                                            return (
                                              <>
                                                {"\n"}
                                                <PortfolioLink
                                                  className={"skip-link"}
                                                  href={"#main"}
                                                >
                                                  {"Skip to content"}
                                                </PortfolioLink>
                                                {"\n"}
                                                <header className={"topbar"}>
                                                  {"\n  "}
                                                  <PortfolioLink
                                                    className={"brand"}
                                                    href={"#home"}
                                                    aria-label={d.home_label}
                                                  >
                                                    <span
                                                      className={"brand-mark"}
                                                    >
                                                      {d.monogram}
                                                    </span>
                                                    <span
                                                      className={"brand-name"}
                                                      data-field={"hero.name"}
                                                    >
                                                      {hero.name}
                                                    </span>
                                                  </PortfolioLink>
                                                  {"\n  "}
                                                  <nav
                                                    className={"topnav"}
                                                    aria-label={
                                                      "Main navigation"
                                                    }
                                                  >
                                                    <PortfolioLink
                                                      href={"#work"}
                                                    >
                                                      {"Work"}
                                                    </PortfolioLink>
                                                    <PortfolioLink
                                                      href={"#about"}
                                                    >
                                                      {"About"}
                                                    </PortfolioLink>
                                                    <PortfolioLink
                                                      className={"topnav-cta"}
                                                      href={"#contact"}
                                                    >
                                                      {"Let's talk"}
                                                    </PortfolioLink>
                                                  </nav>
                                                  {"\n"}
                                                </header>
                                                {"\n"}
                                                <main id={"main"}>
                                                  {"\n"}
                                                  <RouteView
                                                    className={"route-view"}
                                                    id={"home"}
                                                    data-view={""}
                                                    data-title={
                                                      c.metadata.title
                                                    }
                                                  >
                                                    {"\n  "}
                                                    <section
                                                      className={"hero"}
                                                      data-scene={"hero"}
                                                      data-chapter={""}
                                                      aria-labelledby={
                                                        "hero-title"
                                                      }
                                                    >
                                                      {"\n    "}
                                                      <div
                                                        className={"hero-stage"}
                                                      >
                                                        {"\n      "}
                                                        <div
                                                          className={"hero-art"}
                                                          aria-hidden={"true"}
                                                        >
                                                          <span
                                                            className={
                                                              "hero-ring"
                                                            }
                                                          ></span>
                                                          <span
                                                            className={
                                                              "hero-ring"
                                                            }
                                                          ></span>
                                                          <span
                                                            className={
                                                              "hero-ring"
                                                            }
                                                          ></span>
                                                          <span
                                                            className={
                                                              "hero-ring"
                                                            }
                                                          ></span>
                                                          <span
                                                            className={
                                                              "hero-beam"
                                                            }
                                                          ></span>
                                                          <span
                                                            className={
                                                              "hero-bar"
                                                            }
                                                          ></span>
                                                          <span
                                                            className={
                                                              "hero-bar"
                                                            }
                                                          ></span>
                                                          <Dust />
                                                        </div>
                                                        {"\n      "}
                                                        <div
                                                          className={
                                                            "hero-copy"
                                                          }
                                                        >
                                                          {"\n        "}
                                                          {truthy(
                                                            hero.eyebrow_primary,
                                                          ) ? (
                                                            <>
                                                              <p
                                                                className={
                                                                  "eyebrow"
                                                                }
                                                                data-field={
                                                                  "hero.eyebrow_primary"
                                                                }
                                                              >
                                                                {
                                                                  hero.eyebrow_primary
                                                                }
                                                              </p>
                                                            </>
                                                          ) : null}
                                                          {"\n        "}
                                                          <ThemeElement
                                                            as="h1"
                                                            id={"hero-title"}
                                                            data-len={
                                                              d.len.headline
                                                            }
                                                          >
                                                            {truthy(
                                                              hero.headline_prefix,
                                                            ) ? (
                                                              <>
                                                                <span
                                                                  data-field={
                                                                    "hero.headline_prefix"
                                                                  }
                                                                >
                                                                  {
                                                                    hero.headline_prefix
                                                                  }
                                                                </span>
                                                              </>
                                                            ) : null}{" "}
                                                            {truthy(
                                                              hero.headline_emphasis,
                                                            ) ? (
                                                              <>
                                                                <em
                                                                  data-field={
                                                                    "hero.headline_emphasis"
                                                                  }
                                                                >
                                                                  {
                                                                    hero.headline_emphasis
                                                                  }
                                                                </em>
                                                              </>
                                                            ) : null}
                                                          </ThemeElement>
                                                          {"\n        "}
                                                          <p
                                                            className={
                                                              "hero-intro"
                                                            }
                                                            data-field={
                                                              "hero.intro"
                                                            }
                                                          >
                                                            {hero.intro}
                                                          </p>
                                                          {"\n        "}
                                                          <div
                                                            className={
                                                              "hero-actions"
                                                            }
                                                          >
                                                            <PortfolioLink
                                                              className={
                                                                "btn btn-primary"
                                                              }
                                                              href={"#work"}
                                                            >
                                                              {
                                                                "Explore selected work"
                                                              }
                                                            </PortfolioLink>
                                                            <PortfolioLink
                                                              className={
                                                                "btn btn-link"
                                                              }
                                                              href={"#about"}
                                                            >
                                                              {"Get to know me"}
                                                            </PortfolioLink>
                                                          </div>
                                                          {"\n      "}
                                                        </div>
                                                        {"\n      "}
                                                        <p
                                                          className={
                                                            "hero-name"
                                                          }
                                                          data-len={d.len.name}
                                                          data-field={
                                                            "hero.name"
                                                          }
                                                        >
                                                          {hero.name}
                                                        </p>
                                                        {"\n      "}
                                                        {truthy(
                                                          truthy(hero.location)
                                                            ? hero.location
                                                            : hero.eyebrow_secondary,
                                                        ) ? (
                                                          <>
                                                            <p
                                                              className={
                                                                "hero-foot"
                                                              }
                                                            >
                                                              {truthy(
                                                                hero.location,
                                                              ) ? (
                                                                <>
                                                                  <span
                                                                    data-field={
                                                                      "hero.location"
                                                                    }
                                                                  >
                                                                    {
                                                                      hero.location
                                                                    }
                                                                  </span>
                                                                </>
                                                              ) : null}
                                                              {truthy(
                                                                hero.eyebrow_secondary,
                                                              ) ? (
                                                                <>
                                                                  <span
                                                                    data-field={
                                                                      "hero.eyebrow_secondary"
                                                                    }
                                                                  >
                                                                    {
                                                                      hero.eyebrow_secondary
                                                                    }
                                                                  </span>
                                                                </>
                                                              ) : null}
                                                            </p>
                                                          </>
                                                        ) : null}
                                                        {"\n    "}
                                                      </div>
                                                      {"\n  "}
                                                    </section>
                                                    {"\n  "}
                                                    {truthy(
                                                      atlas.statistics,
                                                    ) ? (
                                                      <>
                                                        {"\n  "}
                                                        <section
                                                          className={"proof"}
                                                          data-chapter={""}
                                                          aria-labelledby={
                                                            "proof-title"
                                                          }
                                                        >
                                                          {"\n    "}
                                                          <div
                                                            className={
                                                              "proof-head"
                                                            }
                                                          >
                                                            <ThemeElement
                                                              as="h2"
                                                              className={
                                                                "kicker"
                                                              }
                                                              id={"proof-title"}
                                                            >
                                                              {
                                                                "Selected results"
                                                              }
                                                            </ThemeElement>
                                                            {truthy(
                                                              d.sample
                                                                .statistics,
                                                            ) ? (
                                                              <>
                                                                <p
                                                                  className={
                                                                    "meta"
                                                                  }
                                                                >
                                                                  {
                                                                    "Sample content — replace with your own details."
                                                                  }
                                                                </p>
                                                              </>
                                                            ) : null}
                                                          </div>
                                                          {"\n    "}
                                                          <ul
                                                            className={
                                                              "figures"
                                                            }
                                                            data-count={
                                                              atlas.statistics
                                                                .length
                                                            }
                                                          >
                                                            {atlas.statistics.map(
                                                              (
                                                                stat: any,
                                                                index: number,
                                                                items: any[],
                                                              ) => {
                                                                const loop = {
                                                                  index0: index,
                                                                  index:
                                                                    index + 1,
                                                                  last:
                                                                    index ===
                                                                    items.length -
                                                                      1,
                                                                  first:
                                                                    index === 0,
                                                                };
                                                                return (
                                                                  <Fragment
                                                                    key={index}
                                                                  >
                                                                    <ThemeElement
                                                                      as="li"
                                                                      className={
                                                                        "figure"
                                                                      }
                                                                    >
                                                                      <ThemeElement
                                                                        as="strong"
                                                                        className={
                                                                          "figure-value"
                                                                        }
                                                                        data-field={
                                                                          "" +
                                                                          "atlas.statistics[" +
                                                                          loop.index0 +
                                                                          "].value"
                                                                        }
                                                                      >
                                                                        {
                                                                          stat.value
                                                                        }
                                                                      </ThemeElement>
                                                                      <ThemeElement
                                                                        as="span"
                                                                        className={
                                                                          "figure-label"
                                                                        }
                                                                        data-field={
                                                                          "" +
                                                                          "atlas.statistics[" +
                                                                          loop.index0 +
                                                                          "].label"
                                                                        }
                                                                      >
                                                                        {
                                                                          stat.label
                                                                        }
                                                                      </ThemeElement>
                                                                    </ThemeElement>
                                                                  </Fragment>
                                                                );
                                                              },
                                                            )}
                                                          </ul>
                                                          {"\n  "}
                                                        </section>
                                                        {"\n  "}
                                                      </>
                                                    ) : null}
                                                    {"\n  "}
                                                    {truthy(organizations) ? (
                                                      <>
                                                        {"\n  "}
                                                        <section
                                                          className={
                                                            "worked-with"
                                                          }
                                                          data-chapter={""}
                                                          aria-labelledby={
                                                            "worked-title"
                                                          }
                                                        >
                                                          {"\n    "}
                                                          <ThemeElement
                                                            as="h2"
                                                            className={"kicker"}
                                                            id={"worked-title"}
                                                            data-field={
                                                              "professional_context.eyebrow"
                                                            }
                                                          >
                                                            {context.eyebrow}
                                                          </ThemeElement>
                                                          {"\n    "}
                                                          <ul
                                                            className={"orgs"}
                                                            data-count={
                                                              organizations.length
                                                            }
                                                          >
                                                            {organizations.map(
                                                              (
                                                                organization: any,
                                                                index: number,
                                                                items: any[],
                                                              ) => {
                                                                const loop = {
                                                                  index0: index,
                                                                  index:
                                                                    index + 1,
                                                                  last:
                                                                    index ===
                                                                    items.length -
                                                                      1,
                                                                  first:
                                                                    index === 0,
                                                                };
                                                                return (
                                                                  <Fragment
                                                                    key={index}
                                                                  >
                                                                    <li
                                                                      data-field={
                                                                        "" +
                                                                        "professional_context.organizations[" +
                                                                        loop.index0 +
                                                                        "]"
                                                                      }
                                                                    >
                                                                      {
                                                                        organization
                                                                      }
                                                                    </li>
                                                                  </Fragment>
                                                                );
                                                              },
                                                            )}
                                                          </ul>
                                                          {"\n  "}
                                                        </section>
                                                        {"\n  "}
                                                      </>
                                                    ) : null}
                                                    {"\n  "}
                                                    {truthy(
                                                      c.marquee_keywords,
                                                    ) ? (
                                                      <>
                                                        <div
                                                          className={"ticker"}
                                                          role={"region"}
                                                          aria-label={
                                                            "Areas of practice"
                                                          }
                                                        >
                                                          <ThemeElement
                                                            as="ul"
                                                            className={
                                                              "ticker-track"
                                                            }
                                                          >
                                                            {c.marquee_keywords.map(
                                                              (
                                                                keyword: any,
                                                                index: number,
                                                                items: any[],
                                                              ) => {
                                                                const loop = {
                                                                  index0: index,
                                                                  index:
                                                                    index + 1,
                                                                  last:
                                                                    index ===
                                                                    items.length -
                                                                      1,
                                                                  first:
                                                                    index === 0,
                                                                };
                                                                return (
                                                                  <Fragment
                                                                    key={index}
                                                                  >
                                                                    <li
                                                                      data-field={
                                                                        "" +
                                                                        "marquee_keywords[" +
                                                                        loop.index0 +
                                                                        "]"
                                                                      }
                                                                    >
                                                                      {keyword}
                                                                    </li>
                                                                  </Fragment>
                                                                );
                                                              },
                                                            )}
                                                          </ThemeElement>
                                                        </div>
                                                      </>
                                                    ) : null}
                                                    {"\n  "}
                                                    <section
                                                      className={"thesis"}
                                                      data-chapter={""}
                                                      aria-labelledby={
                                                        "thesis-title"
                                                      }
                                                    >
                                                      {"\n    "}
                                                      {truthy(
                                                        practice.eyebrow,
                                                      ) ? (
                                                        <>
                                                          <p
                                                            className={"kicker"}
                                                            data-field={
                                                              "systems_practice.eyebrow"
                                                            }
                                                          >
                                                            {practice.eyebrow}
                                                          </p>
                                                        </>
                                                      ) : null}
                                                      {"\n    "}
                                                      <ThemeElement
                                                        as="h2"
                                                        className={
                                                          "thesis-statement"
                                                        }
                                                        id={"thesis-title"}
                                                        data-len={d.len.thesis}
                                                        data-field={
                                                          "systems_practice.heading"
                                                        }
                                                      >
                                                        {practice.heading}
                                                      </ThemeElement>
                                                      {"\n    "}
                                                      {truthy(
                                                        practice.intro,
                                                      ) ? (
                                                        <>
                                                          <ThemeElement
                                                            as="p"
                                                            className={
                                                              "thesis-intro"
                                                            }
                                                            data-field={
                                                              "systems_practice.intro"
                                                            }
                                                          >
                                                            {practice.intro}
                                                          </ThemeElement>
                                                        </>
                                                      ) : null}
                                                      {"\n    "}
                                                      <ol
                                                        className={"pillars"}
                                                        data-count={
                                                          practice.pillars
                                                            .length
                                                        }
                                                      >
                                                        {practice.pillars.map(
                                                          (
                                                            pillar: any,
                                                            index: number,
                                                            items: any[],
                                                          ) => {
                                                            const loop = {
                                                              index0: index,
                                                              index: index + 1,
                                                              last:
                                                                index ===
                                                                items.length -
                                                                  1,
                                                              first:
                                                                index === 0,
                                                            };
                                                            return (
                                                              <Fragment
                                                                key={index}
                                                              >
                                                                <ThemeElement
                                                                  as="li"
                                                                  className={
                                                                    "pillar"
                                                                  }
                                                                >
                                                                  <h3
                                                                    data-field={
                                                                      "" +
                                                                      "systems_practice.pillars[" +
                                                                      loop.index0 +
                                                                      "].title"
                                                                    }
                                                                  >
                                                                    {
                                                                      pillar.title
                                                                    }
                                                                  </h3>
                                                                  <p
                                                                    data-field={
                                                                      "" +
                                                                      "systems_practice.pillars[" +
                                                                      loop.index0 +
                                                                      "].description"
                                                                    }
                                                                  >
                                                                    {
                                                                      pillar.description
                                                                    }
                                                                  </p>
                                                                </ThemeElement>
                                                              </Fragment>
                                                            );
                                                          },
                                                        )}
                                                      </ol>
                                                      {"\n  "}
                                                    </section>
                                                    {"\n  "}
                                                    <section
                                                      className={"work"}
                                                      id={"work"}
                                                      data-chapter={""}
                                                      aria-labelledby={
                                                        "work-title"
                                                      }
                                                    >
                                                      {"\n    "}
                                                      <div
                                                        className={
                                                          "section-head"
                                                        }
                                                      >
                                                        <ThemeElement
                                                          as="h2"
                                                          className={
                                                            "section-title"
                                                          }
                                                          id={"work-title"}
                                                        >
                                                          {"Selected work"}
                                                        </ThemeElement>
                                                      </div>
                                                      {"\n    "}
                                                      {truthy(
                                                        atlas.projects,
                                                      ) ? (
                                                        <>
                                                          {"\n    "}
                                                          <div
                                                            className={
                                                              "work-list"
                                                            }
                                                            data-count={
                                                              atlas.projects
                                                                .length
                                                            }
                                                          >
                                                            {"\n      "}
                                                            {atlas.projects.map(
                                                              (
                                                                project: any,
                                                                index: number,
                                                                items: any[],
                                                              ) => {
                                                                const loop = {
                                                                  index0: index,
                                                                  index:
                                                                    index + 1,
                                                                  last:
                                                                    index ===
                                                                    items.length -
                                                                      1,
                                                                  first:
                                                                    index === 0,
                                                                };
                                                                return (
                                                                  <Fragment
                                                                    key={index}
                                                                  >
                                                                    {"\n      "}
                                                                    {(() => {
                                                                      const isCase =
                                                                        truthy(
                                                                          project.problem,
                                                                        )
                                                                          ? project.approach
                                                                          : project.problem;
                                                                      return (
                                                                        <>
                                                                          {
                                                                            "\n      "
                                                                          }
                                                                          <ProjectLink
                                                                            className={
                                                                              "project"
                                                                            }
                                                                            project={
                                                                              project
                                                                            }
                                                                            index={
                                                                              loop.index
                                                                            }
                                                                          >
                                                                            {
                                                                              "\n        "
                                                                            }
                                                                            <div
                                                                              className={
                                                                                "poster"
                                                                              }
                                                                              data-art={
                                                                                d
                                                                                  .arts[
                                                                                  loop
                                                                                    .index0
                                                                                ]
                                                                              }
                                                                              data-tone={
                                                                                (loop.index0 %
                                                                                  4) +
                                                                                1
                                                                              }
                                                                              aria-hidden={
                                                                                "true"
                                                                              }
                                                                            ></div>
                                                                            {
                                                                              "\n        "
                                                                            }
                                                                            <div
                                                                              className={
                                                                                "project-info"
                                                                              }
                                                                            >
                                                                              {
                                                                                "\n          "
                                                                              }
                                                                              <p
                                                                                className={
                                                                                  "project-kind"
                                                                                }
                                                                              >
                                                                                {truthy(
                                                                                  project.kind ===
                                                                                    "illustrative",
                                                                                ) ? (
                                                                                  <>
                                                                                    {
                                                                                      "Illustrative concept — not real client work"
                                                                                    }
                                                                                  </>
                                                                                ) : (
                                                                                  <>
                                                                                    {
                                                                                      "Selected project"
                                                                                    }
                                                                                  </>
                                                                                )}
                                                                              </p>
                                                                              {
                                                                                "\n          "
                                                                              }
                                                                              <h3
                                                                                data-field={
                                                                                  "" +
                                                                                  "atlas.projects[" +
                                                                                  loop.index0 +
                                                                                  "].title"
                                                                                }
                                                                              >
                                                                                {
                                                                                  project.title
                                                                                }
                                                                              </h3>
                                                                              {
                                                                                "\n          "
                                                                              }
                                                                              <p
                                                                                className={
                                                                                  "project-summary"
                                                                                }
                                                                                data-field={
                                                                                  "" +
                                                                                  "atlas.projects[" +
                                                                                  loop.index0 +
                                                                                  "].summary"
                                                                                }
                                                                              >
                                                                                {
                                                                                  project.summary
                                                                                }
                                                                              </p>
                                                                              {
                                                                                "\n          "
                                                                              }
                                                                              {truthy(
                                                                                truthy(
                                                                                  project.role,
                                                                                )
                                                                                  ? project.role
                                                                                  : project.period,
                                                                              ) ? (
                                                                                <>
                                                                                  <p
                                                                                    className={
                                                                                      "project-meta"
                                                                                    }
                                                                                  >
                                                                                    {truthy(
                                                                                      project.role,
                                                                                    ) ? (
                                                                                      <>
                                                                                        <span
                                                                                          data-field={
                                                                                            "" +
                                                                                            "atlas.projects[" +
                                                                                            loop.index0 +
                                                                                            "].role"
                                                                                          }
                                                                                        >
                                                                                          {
                                                                                            project.role
                                                                                          }
                                                                                        </span>
                                                                                      </>
                                                                                    ) : null}
                                                                                    {truthy(
                                                                                      project.period,
                                                                                    ) ? (
                                                                                      <>
                                                                                        <span
                                                                                          data-field={
                                                                                            "" +
                                                                                            "atlas.projects[" +
                                                                                            loop.index0 +
                                                                                            "].period"
                                                                                          }
                                                                                        >
                                                                                          {
                                                                                            project.period
                                                                                          }
                                                                                        </span>
                                                                                      </>
                                                                                    ) : null}
                                                                                  </p>
                                                                                </>
                                                                              ) : null}
                                                                              {
                                                                                "\n          "
                                                                              }
                                                                              {truthy(
                                                                                isCase,
                                                                              ) ? (
                                                                                <>
                                                                                  <span
                                                                                    className={
                                                                                      "project-cta"
                                                                                    }
                                                                                  >
                                                                                    {
                                                                                      "View case study"
                                                                                    }
                                                                                  </span>
                                                                                </>
                                                                              ) : (
                                                                                <>
                                                                                  {truthy(
                                                                                    project.external_url,
                                                                                  ) ? (
                                                                                    <>
                                                                                      <span
                                                                                        className={
                                                                                          "project-cta"
                                                                                        }
                                                                                      >
                                                                                        {
                                                                                          "Visit project"
                                                                                        }
                                                                                      </span>
                                                                                    </>
                                                                                  ) : null}
                                                                                </>
                                                                              )}
                                                                              {
                                                                                "\n        "
                                                                              }
                                                                            </div>
                                                                            {
                                                                              "\n      "
                                                                            }
                                                                          </ProjectLink>
                                                                          {
                                                                            "\n      "
                                                                          }
                                                                        </>
                                                                      );
                                                                    })()}
                                                                  </Fragment>
                                                                );
                                                              },
                                                            )}
                                                            {"\n    "}
                                                          </div>
                                                          {"\n    "}
                                                        </>
                                                      ) : (
                                                        <>
                                                          {"\n    "}
                                                          <ThemeElement
                                                            as="div"
                                                            className={
                                                              "work-empty"
                                                            }
                                                          >
                                                            <div
                                                              className={
                                                                "poster"
                                                              }
                                                              data-art={
                                                                "aperture"
                                                              }
                                                              data-tone={"1"}
                                                              aria-hidden={
                                                                "true"
                                                              }
                                                            ></div>
                                                            <div
                                                              className={
                                                                "project-info"
                                                              }
                                                            >
                                                              <p
                                                                className={
                                                                  "kicker"
                                                                }
                                                              >
                                                                {
                                                                  "Work in progress"
                                                                }
                                                              </p>
                                                              <h3>
                                                                {
                                                                  "Your story can grow here."
                                                                }
                                                              </h3>
                                                              <p>
                                                                {
                                                                  "Project details can be added whenever you're ready."
                                                                }
                                                              </p>
                                                            </div>
                                                          </ThemeElement>
                                                          {"\n    "}
                                                        </>
                                                      )}
                                                      {"\n  "}
                                                    </section>
                                                    {"\n  "}
                                                    <section
                                                      className={"about-teaser"}
                                                      data-chapter={""}
                                                      aria-labelledby={
                                                        "teaser-title"
                                                      }
                                                    >
                                                      {"\n    "}
                                                      <figure
                                                        className={"portrait"}
                                                        data-initials={
                                                          d.monogram
                                                        }
                                                      ></figure>
                                                      {"\n    "}
                                                      <div
                                                        className={
                                                          "about-teaser-copy"
                                                        }
                                                      >
                                                        {"\n      "}
                                                        <p className={"kicker"}>
                                                          {"About"}
                                                        </p>
                                                        {"\n      "}
                                                        <ThemeElement
                                                          as="h2"
                                                          id={"teaser-title"}
                                                          data-len={d.len.about}
                                                          data-field={
                                                            "atlas.about_heading"
                                                          }
                                                        >
                                                          {atlas.about_heading}
                                                        </ThemeElement>
                                                        {"\n      "}
                                                        <p
                                                          className={
                                                            "about-teaser-text"
                                                          }
                                                          data-field={
                                                            "atlas.about_intro"
                                                          }
                                                        >
                                                          {atlas.about_intro}
                                                        </p>
                                                        {"\n      "}
                                                        <PortfolioLink
                                                          className={
                                                            "btn btn-link"
                                                          }
                                                          href={"#about"}
                                                        >
                                                          {"Get to know me"}
                                                        </PortfolioLink>
                                                        {"\n    "}
                                                      </div>
                                                      {"\n  "}
                                                    </section>
                                                    {"\n  "}
                                                    <section
                                                      className={"credits"}
                                                      id={"contact"}
                                                      data-chapter={""}
                                                      aria-labelledby={
                                                        "contact-title"
                                                      }
                                                    >
                                                      {"\n    "}
                                                      {truthy(
                                                        connect.eyebrow,
                                                      ) ? (
                                                        <>
                                                          <p
                                                            className={"kicker"}
                                                            data-field={
                                                              "connect.eyebrow"
                                                            }
                                                          >
                                                            {connect.eyebrow}
                                                          </p>
                                                        </>
                                                      ) : null}
                                                      {"\n    "}
                                                      <ThemeElement
                                                        as="h2"
                                                        id={"contact-title"}
                                                        data-len={d.len.connect}
                                                        data-field={
                                                          "connect.heading"
                                                        }
                                                      >
                                                        {connect.heading}
                                                      </ThemeElement>
                                                      {"\n    "}
                                                      {truthy(connect.intro) ? (
                                                        <>
                                                          <ThemeElement
                                                            as="p"
                                                            className={
                                                              "credits-intro"
                                                            }
                                                            data-field={
                                                              "connect.intro"
                                                            }
                                                          >
                                                            {connect.intro}
                                                          </ThemeElement>
                                                        </>
                                                      ) : null}
                                                      {"\n    "}
                                                      {truthy(
                                                        connect.destinations,
                                                      ) ? (
                                                        <>
                                                          <ul
                                                            className={
                                                              "destinations"
                                                            }
                                                            data-count={
                                                              connect
                                                                .destinations
                                                                .length
                                                            }
                                                          >
                                                            {connect.destinations.map(
                                                              (
                                                                destination: any,
                                                                index: number,
                                                                items: any[],
                                                              ) => {
                                                                const loop = {
                                                                  index0: index,
                                                                  index:
                                                                    index + 1,
                                                                  last:
                                                                    index ===
                                                                    items.length -
                                                                      1,
                                                                  first:
                                                                    index === 0,
                                                                };
                                                                return (
                                                                  <Fragment
                                                                    key={index}
                                                                  >
                                                                    <li>
                                                                      <PortfolioLink
                                                                        className={
                                                                          "destination"
                                                                        }
                                                                        href={
                                                                          destination.url
                                                                        }
                                                                        {...(truthy(
                                                                          destination.url.startsWith(
                                                                            "http",
                                                                          ),
                                                                        )
                                                                          ? {
                                                                              target:
                                                                                "_blank",
                                                                              rel: "noopener noreferrer",
                                                                            }
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
                                                                          {
                                                                            destination.label
                                                                          }
                                                                        </span>
                                                                      </PortfolioLink>
                                                                    </li>
                                                                  </Fragment>
                                                                );
                                                              },
                                                            )}
                                                          </ul>
                                                        </>
                                                      ) : null}
                                                      {"\n  "}
                                                    </section>
                                                    {"\n"}
                                                  </RouteView>
                                                  {"\n"}
                                                  <RouteView
                                                    className={
                                                      "route-view inner-page"
                                                    }
                                                    id={"about"}
                                                    data-view={""}
                                                    data-title={
                                                      "" +
                                                      "About — " +
                                                      hero.name
                                                    }
                                                  >
                                                    {"\n  "}
                                                    <section
                                                      className={"page-head"}
                                                      data-chapter={""}
                                                    >
                                                      {"\n    "}
                                                      <div
                                                        className={
                                                          "page-head-copy"
                                                        }
                                                      >
                                                        {"\n      "}
                                                        <p className={"kicker"}>
                                                          {"About"}
                                                        </p>
                                                        {"\n      "}
                                                        <ThemeElement
                                                          as="h1"
                                                          data-len={d.len.about}
                                                          data-field={
                                                            "atlas.about_heading"
                                                          }
                                                        >
                                                          {atlas.about_heading}
                                                        </ThemeElement>
                                                        {"\n      "}
                                                        <ThemeElement
                                                          as="p"
                                                          className={"lede"}
                                                          data-field={
                                                            "atlas.about_intro"
                                                          }
                                                        >
                                                          {atlas.about_intro}
                                                        </ThemeElement>
                                                        {"\n      "}
                                                        <PortfolioLink
                                                          className={
                                                            "btn btn-link"
                                                          }
                                                          href={"#contact"}
                                                        >
                                                          {"Get in touch"}
                                                        </PortfolioLink>
                                                        {"\n    "}
                                                      </div>
                                                      {"\n    "}
                                                      <figure
                                                        className={"portrait"}
                                                        data-initials={
                                                          d.monogram
                                                        }
                                                      ></figure>
                                                      {"\n  "}
                                                    </section>
                                                    {"\n  "}
                                                    {truthy(
                                                      atlas.about_quote,
                                                    ) ? (
                                                      <>
                                                        <section
                                                          className={"pull"}
                                                          data-chapter={""}
                                                        >
                                                          <blockquote
                                                            data-field={
                                                              "atlas.about_quote"
                                                            }
                                                          >
                                                            {atlas.about_quote}
                                                          </blockquote>
                                                        </section>
                                                      </>
                                                    ) : null}
                                                    {"\n  "}
                                                    {truthy(
                                                      atlas.experience,
                                                    ) ? (
                                                      <>
                                                        {"\n  "}
                                                        <section
                                                          className={
                                                            "experience"
                                                          }
                                                          data-chapter={""}
                                                          aria-labelledby={
                                                            "experience-title"
                                                          }
                                                        >
                                                          {"\n    "}
                                                          <div
                                                            className={
                                                              "section-head"
                                                            }
                                                          >
                                                            <ThemeElement
                                                              as="h2"
                                                              className={
                                                                "section-title"
                                                              }
                                                              id={
                                                                "experience-title"
                                                              }
                                                            >
                                                              {"Experience"}
                                                            </ThemeElement>
                                                            {truthy(
                                                              d.sample
                                                                .experience,
                                                            ) ? (
                                                              <>
                                                                <p
                                                                  className={
                                                                    "meta"
                                                                  }
                                                                >
                                                                  {
                                                                    "Sample content — replace with your own details."
                                                                  }
                                                                </p>
                                                              </>
                                                            ) : null}
                                                          </div>
                                                          {"\n    "}
                                                          <ol
                                                            className={"ledger"}
                                                            data-count={
                                                              atlas.experience
                                                                .length
                                                            }
                                                          >
                                                            {atlas.experience.map(
                                                              (
                                                                row: any,
                                                                index: number,
                                                                items: any[],
                                                              ) => {
                                                                const loop = {
                                                                  index0: index,
                                                                  index:
                                                                    index + 1,
                                                                  last:
                                                                    index ===
                                                                    items.length -
                                                                      1,
                                                                  first:
                                                                    index === 0,
                                                                };
                                                                return (
                                                                  <Fragment
                                                                    key={index}
                                                                  >
                                                                    <ThemeElement
                                                                      as="li"
                                                                      className={
                                                                        "ledger-row"
                                                                      }
                                                                    >
                                                                      <p
                                                                        className={
                                                                          "ledger-dates"
                                                                        }
                                                                        data-field={
                                                                          "" +
                                                                          "atlas.experience[" +
                                                                          loop.index0 +
                                                                          "].dates"
                                                                        }
                                                                      >
                                                                        {
                                                                          row.dates
                                                                        }
                                                                      </p>
                                                                      <div
                                                                        className={
                                                                          "ledger-main"
                                                                        }
                                                                      >
                                                                        <h3
                                                                          data-field={
                                                                            "" +
                                                                            "atlas.experience[" +
                                                                            loop.index0 +
                                                                            "].role"
                                                                          }
                                                                        >
                                                                          {
                                                                            row.role
                                                                          }
                                                                        </h3>
                                                                        <p
                                                                          className={
                                                                            "ledger-org"
                                                                          }
                                                                          data-field={
                                                                            "" +
                                                                            "atlas.experience[" +
                                                                            loop.index0 +
                                                                            "].organization"
                                                                          }
                                                                        >
                                                                          {
                                                                            row.organization
                                                                          }
                                                                        </p>
                                                                        <p
                                                                          className={
                                                                            "ledger-text"
                                                                          }
                                                                          data-field={
                                                                            "" +
                                                                            "atlas.experience[" +
                                                                            loop.index0 +
                                                                            "].description"
                                                                          }
                                                                        >
                                                                          {
                                                                            row.description
                                                                          }
                                                                        </p>
                                                                      </div>
                                                                    </ThemeElement>
                                                                  </Fragment>
                                                                );
                                                              },
                                                            )}
                                                          </ol>
                                                          {"\n  "}
                                                        </section>
                                                        {"\n  "}
                                                      </>
                                                    ) : null}
                                                    {"\n  "}
                                                    <section
                                                      className={"practice"}
                                                      data-chapter={""}
                                                      aria-labelledby={
                                                        "practice-title"
                                                      }
                                                    >
                                                      {"\n    "}
                                                      <div
                                                        className={
                                                          "section-head"
                                                        }
                                                      >
                                                        {truthy(
                                                          caps.eyebrow,
                                                        ) ? (
                                                          <>
                                                            <p
                                                              className={
                                                                "kicker"
                                                              }
                                                              data-field={
                                                                "technical_capabilities.eyebrow"
                                                              }
                                                            >
                                                              {caps.eyebrow}
                                                            </p>
                                                          </>
                                                        ) : null}
                                                        <ThemeElement
                                                          as="h2"
                                                          className={
                                                            "section-title"
                                                          }
                                                          id={"practice-title"}
                                                          data-field={
                                                            "technical_capabilities.heading"
                                                          }
                                                        >
                                                          {caps.heading}
                                                        </ThemeElement>
                                                      </div>
                                                      {"\n    "}
                                                      <div
                                                        className={"groups"}
                                                        data-count={
                                                          caps.groups.length
                                                        }
                                                      >
                                                        {caps.groups.map(
                                                          (
                                                            group: any,
                                                            index: number,
                                                            items: any[],
                                                          ) => {
                                                            const loop = {
                                                              index0: index,
                                                              index: index + 1,
                                                              last:
                                                                index ===
                                                                items.length -
                                                                  1,
                                                              first:
                                                                index === 0,
                                                            };
                                                            return (
                                                              <Fragment
                                                                key={index}
                                                              >
                                                                {(() => {
                                                                  const group_index =
                                                                    loop.index0;
                                                                  return (
                                                                    <>
                                                                      <ThemeElement
                                                                        as="div"
                                                                        className={
                                                                          "group"
                                                                        }
                                                                      >
                                                                        <h3
                                                                          data-field={
                                                                            "" +
                                                                            "technical_capabilities.groups[" +
                                                                            group_index +
                                                                            "].heading"
                                                                          }
                                                                        >
                                                                          {
                                                                            group.heading
                                                                          }
                                                                        </h3>
                                                                        <ul>
                                                                          {group[
                                                                            "items"
                                                                          ].map(
                                                                            (
                                                                              item: any,
                                                                              index: number,
                                                                              items: any[],
                                                                            ) => {
                                                                              const loop =
                                                                                {
                                                                                  index0:
                                                                                    index,
                                                                                  index:
                                                                                    index +
                                                                                    1,
                                                                                  last:
                                                                                    index ===
                                                                                    items.length -
                                                                                      1,
                                                                                  first:
                                                                                    index ===
                                                                                    0,
                                                                                };
                                                                              return (
                                                                                <Fragment
                                                                                  key={
                                                                                    index
                                                                                  }
                                                                                >
                                                                                  <li
                                                                                    data-field={
                                                                                      "" +
                                                                                      "technical_capabilities.groups[" +
                                                                                      group_index +
                                                                                      "].items[" +
                                                                                      loop.index0 +
                                                                                      "]"
                                                                                    }
                                                                                  >
                                                                                    {
                                                                                      item
                                                                                    }
                                                                                  </li>
                                                                                </Fragment>
                                                                              );
                                                                            },
                                                                          )}
                                                                        </ul>
                                                                      </ThemeElement>
                                                                    </>
                                                                  );
                                                                })()}
                                                              </Fragment>
                                                            );
                                                          },
                                                        )}
                                                      </div>
                                                      {"\n  "}
                                                    </section>
                                                    {"\n  "}
                                                    {truthy(atlas.education) ? (
                                                      <>
                                                        {"\n  "}
                                                        <section
                                                          className={
                                                            "education"
                                                          }
                                                          data-chapter={""}
                                                          aria-labelledby={
                                                            "education-title"
                                                          }
                                                        >
                                                          {"\n    "}
                                                          <div
                                                            className={
                                                              "section-head"
                                                            }
                                                          >
                                                            <ThemeElement
                                                              as="h2"
                                                              className={
                                                                "section-title"
                                                              }
                                                              id={
                                                                "education-title"
                                                              }
                                                            >
                                                              {"Education"}
                                                            </ThemeElement>
                                                            {truthy(
                                                              d.sample
                                                                .education,
                                                            ) ? (
                                                              <>
                                                                <p
                                                                  className={
                                                                    "meta"
                                                                  }
                                                                >
                                                                  {
                                                                    "Sample content — replace with your own details."
                                                                  }
                                                                </p>
                                                              </>
                                                            ) : null}
                                                          </div>
                                                          {"\n    "}
                                                          <ol
                                                            className={"ledger"}
                                                            data-count={
                                                              atlas.education
                                                                .length
                                                            }
                                                          >
                                                            {atlas.education.map(
                                                              (
                                                                row: any,
                                                                index: number,
                                                                items: any[],
                                                              ) => {
                                                                const loop = {
                                                                  index0: index,
                                                                  index:
                                                                    index + 1,
                                                                  last:
                                                                    index ===
                                                                    items.length -
                                                                      1,
                                                                  first:
                                                                    index === 0,
                                                                };
                                                                return (
                                                                  <Fragment
                                                                    key={index}
                                                                  >
                                                                    <ThemeElement
                                                                      as="li"
                                                                      className={
                                                                        "ledger-row"
                                                                      }
                                                                    >
                                                                      <p
                                                                        className={
                                                                          "ledger-dates"
                                                                        }
                                                                        data-field={
                                                                          "" +
                                                                          "atlas.education[" +
                                                                          loop.index0 +
                                                                          "].dates"
                                                                        }
                                                                      >
                                                                        {
                                                                          row.dates
                                                                        }
                                                                      </p>
                                                                      <div
                                                                        className={
                                                                          "ledger-main"
                                                                        }
                                                                      >
                                                                        <h3
                                                                          data-field={
                                                                            "" +
                                                                            "atlas.education[" +
                                                                            loop.index0 +
                                                                            "].credential"
                                                                          }
                                                                        >
                                                                          {
                                                                            row.credential
                                                                          }
                                                                        </h3>
                                                                        <p
                                                                          className={
                                                                            "ledger-org"
                                                                          }
                                                                          data-field={
                                                                            "" +
                                                                            "atlas.education[" +
                                                                            loop.index0 +
                                                                            "].institution"
                                                                          }
                                                                        >
                                                                          {
                                                                            row.institution
                                                                          }
                                                                        </p>
                                                                      </div>
                                                                    </ThemeElement>
                                                                  </Fragment>
                                                                );
                                                              },
                                                            )}
                                                          </ol>
                                                          {"\n  "}
                                                        </section>
                                                        {"\n  "}
                                                      </>
                                                    ) : null}
                                                    {"\n  "}
                                                    <section
                                                      className={"page-next"}
                                                    >
                                                      <p className={"kicker"}>
                                                        {"Next"}
                                                      </p>
                                                      <PortfolioLink
                                                        className={
                                                          "btn btn-link"
                                                        }
                                                        href={"#work"}
                                                      >
                                                        {"See the work"}
                                                      </PortfolioLink>
                                                    </section>
                                                    {"\n"}
                                                  </RouteView>
                                                  {"\n"}
                                                  {atlas.projects.map(
                                                    (
                                                      project: any,
                                                      index: number,
                                                      items: any[],
                                                    ) => {
                                                      const loop = {
                                                        index0: index,
                                                        index: index + 1,
                                                        last:
                                                          index ===
                                                          items.length - 1,
                                                        first: index === 0,
                                                      };
                                                      return (
                                                        <Fragment key={index}>
                                                          {"\n"}
                                                          {truthy(
                                                            truthy(
                                                              project.problem,
                                                            )
                                                              ? project.approach
                                                              : project.problem,
                                                          ) ? (
                                                            <>
                                                              {"\n"}
                                                              <RouteView
                                                                className={
                                                                  "route-view inner-page case-page"
                                                                }
                                                                id={
                                                                  "" +
                                                                  "case-" +
                                                                  loop.index
                                                                }
                                                                data-view={""}
                                                                data-title={
                                                                  "" +
                                                                  project.title +
                                                                  " — " +
                                                                  hero.name
                                                                }
                                                              >
                                                                {"\n  "}
                                                                <section
                                                                  className={
                                                                    "case-head"
                                                                  }
                                                                  data-chapter={
                                                                    ""
                                                                  }
                                                                >
                                                                  {"\n    "}
                                                                  <PortfolioLink
                                                                    className={
                                                                      "back-link"
                                                                    }
                                                                    href={
                                                                      "#work"
                                                                    }
                                                                  >
                                                                    {"All work"}
                                                                  </PortfolioLink>
                                                                  {"\n    "}
                                                                  <p
                                                                    className={
                                                                      "kicker"
                                                                    }
                                                                  >
                                                                    {truthy(
                                                                      project.kind ===
                                                                        "illustrative",
                                                                    ) ? (
                                                                      <>
                                                                        {
                                                                          "Illustrative concept — not real client work"
                                                                        }
                                                                      </>
                                                                    ) : (
                                                                      <>
                                                                        {
                                                                          "Case study"
                                                                        }
                                                                      </>
                                                                    )}
                                                                  </p>
                                                                  {"\n    "}
                                                                  <ThemeElement
                                                                    as="h1"
                                                                    data-len={
                                                                      d.len
                                                                        .titles[
                                                                        loop
                                                                          .index0
                                                                      ]
                                                                    }
                                                                    data-field={
                                                                      "" +
                                                                      "atlas.projects[" +
                                                                      loop.index0 +
                                                                      "].title"
                                                                    }
                                                                  >
                                                                    {
                                                                      project.title
                                                                    }
                                                                  </ThemeElement>
                                                                  {"\n    "}
                                                                  <ThemeElement
                                                                    as="p"
                                                                    className={
                                                                      "lede"
                                                                    }
                                                                    data-field={
                                                                      "" +
                                                                      "atlas.projects[" +
                                                                      loop.index0 +
                                                                      "].summary"
                                                                    }
                                                                  >
                                                                    {
                                                                      project.summary
                                                                    }
                                                                  </ThemeElement>
                                                                  {"\n    "}
                                                                  {truthy(
                                                                    truthy(
                                                                      project.role,
                                                                    )
                                                                      ? project.role
                                                                      : project.period,
                                                                  ) ? (
                                                                    <>
                                                                      <ThemeElement
                                                                        as="dl"
                                                                        className={
                                                                          "facts"
                                                                        }
                                                                      >
                                                                        {truthy(
                                                                          project.role,
                                                                        ) ? (
                                                                          <>
                                                                            <div>
                                                                              <dt>
                                                                                {
                                                                                  "Role"
                                                                                }
                                                                              </dt>
                                                                              <dd
                                                                                data-field={
                                                                                  "" +
                                                                                  "atlas.projects[" +
                                                                                  loop.index0 +
                                                                                  "].role"
                                                                                }
                                                                              >
                                                                                {
                                                                                  project.role
                                                                                }
                                                                              </dd>
                                                                            </div>
                                                                          </>
                                                                        ) : null}
                                                                        {truthy(
                                                                          project.period,
                                                                        ) ? (
                                                                          <>
                                                                            <div>
                                                                              <dt>
                                                                                {
                                                                                  "Period"
                                                                                }
                                                                              </dt>
                                                                              <dd
                                                                                data-field={
                                                                                  "" +
                                                                                  "atlas.projects[" +
                                                                                  loop.index0 +
                                                                                  "].period"
                                                                                }
                                                                              >
                                                                                {
                                                                                  project.period
                                                                                }
                                                                              </dd>
                                                                            </div>
                                                                          </>
                                                                        ) : null}
                                                                      </ThemeElement>
                                                                    </>
                                                                  ) : null}
                                                                  {"\n  "}
                                                                </section>
                                                                {"\n  "}
                                                                <section
                                                                  className={
                                                                    "case-art"
                                                                  }
                                                                  data-chapter={
                                                                    ""
                                                                  }
                                                                >
                                                                  <div
                                                                    className={
                                                                      "poster poster-wide"
                                                                    }
                                                                    data-art={
                                                                      d.arts[
                                                                        loop
                                                                          .index0
                                                                      ]
                                                                    }
                                                                    data-tone={
                                                                      (loop.index0 %
                                                                        4) +
                                                                      1
                                                                    }
                                                                    role={"img"}
                                                                    aria-label={
                                                                      "Abstract artwork"
                                                                    }
                                                                  ></div>
                                                                  <p
                                                                    className={
                                                                      "note"
                                                                    }
                                                                  >
                                                                    {
                                                                      "Conceptual artwork — illustrative, not a product screenshot."
                                                                    }
                                                                  </p>
                                                                </section>
                                                                {"\n  "}
                                                                <section
                                                                  className={
                                                                    "case-body"
                                                                  }
                                                                  data-chapter={
                                                                    ""
                                                                  }
                                                                >
                                                                  {"\n    "}
                                                                  <ThemeElement
                                                                    as="div"
                                                                    className={
                                                                      "case-step"
                                                                    }
                                                                  >
                                                                    <ThemeElement as="h2">
                                                                      {
                                                                        "Problem"
                                                                      }
                                                                    </ThemeElement>
                                                                    <p
                                                                      data-field={
                                                                        "" +
                                                                        "atlas.projects[" +
                                                                        loop.index0 +
                                                                        "].problem"
                                                                      }
                                                                    >
                                                                      {
                                                                        project.problem
                                                                      }
                                                                    </p>
                                                                  </ThemeElement>
                                                                  {"\n    "}
                                                                  <ThemeElement
                                                                    as="div"
                                                                    className={
                                                                      "case-step"
                                                                    }
                                                                  >
                                                                    <ThemeElement as="h2">
                                                                      {
                                                                        "Approach"
                                                                      }
                                                                    </ThemeElement>
                                                                    <p
                                                                      data-field={
                                                                        "" +
                                                                        "atlas.projects[" +
                                                                        loop.index0 +
                                                                        "].approach"
                                                                      }
                                                                    >
                                                                      {
                                                                        project.approach
                                                                      }
                                                                    </p>
                                                                  </ThemeElement>
                                                                  {"\n    "}
                                                                  {truthy(
                                                                    project.outcome,
                                                                  ) ? (
                                                                    <>
                                                                      <ThemeElement
                                                                        as="div"
                                                                        className={
                                                                          "case-step case-result"
                                                                        }
                                                                      >
                                                                        <ThemeElement as="h2">
                                                                          {
                                                                            "Outcome"
                                                                          }
                                                                        </ThemeElement>
                                                                        <p
                                                                          data-field={
                                                                            "" +
                                                                            "atlas.projects[" +
                                                                            loop.index0 +
                                                                            "].outcome"
                                                                          }
                                                                        >
                                                                          {
                                                                            project.outcome
                                                                          }
                                                                        </p>
                                                                      </ThemeElement>
                                                                    </>
                                                                  ) : null}
                                                                  {"\n  "}
                                                                </section>
                                                                {"\n  "}
                                                                <section
                                                                  className={
                                                                    "page-next"
                                                                  }
                                                                >
                                                                  <p
                                                                    className={
                                                                      "kicker"
                                                                    }
                                                                  >
                                                                    {"Next"}
                                                                  </p>
                                                                  <PortfolioLink
                                                                    className={
                                                                      "btn btn-link"
                                                                    }
                                                                    href={
                                                                      "#work"
                                                                    }
                                                                  >
                                                                    {
                                                                      "Explore all work"
                                                                    }
                                                                  </PortfolioLink>
                                                                  {truthy(
                                                                    project.external_url,
                                                                  ) ? (
                                                                    <>
                                                                      <PortfolioLink
                                                                        className={
                                                                          "btn btn-link"
                                                                        }
                                                                        href={
                                                                          project.external_url
                                                                        }
                                                                        target={
                                                                          "_blank"
                                                                        }
                                                                        rel={
                                                                          "noopener noreferrer"
                                                                        }
                                                                      >
                                                                        {
                                                                          "Visit project"
                                                                        }
                                                                      </PortfolioLink>
                                                                    </>
                                                                  ) : null}
                                                                </section>
                                                                {"\n"}
                                                              </RouteView>
                                                              {"\n"}
                                                            </>
                                                          ) : null}
                                                          {"\n"}
                                                        </Fragment>
                                                      );
                                                    },
                                                  )}
                                                  {"\n"}
                                                </main>
                                                {"\n"}
                                                <footer
                                                  className={"site-footer"}
                                                >
                                                  <PortfolioLink
                                                    className={"brand"}
                                                    href={"#home"}
                                                    aria-label={d.home_label}
                                                  >
                                                    <span
                                                      className={"brand-mark"}
                                                    >
                                                      {d.monogram}
                                                    </span>
                                                    <span
                                                      className={"brand-name"}
                                                      data-field={"hero.name"}
                                                    >
                                                      {hero.name}
                                                    </span>
                                                  </PortfolioLink>
                                                  <nav
                                                    className={"footer-nav"}
                                                    aria-label={
                                                      "Footer navigation"
                                                    }
                                                  >
                                                    <PortfolioLink
                                                      href={"#work"}
                                                    >
                                                      {"Work"}
                                                    </PortfolioLink>
                                                    <PortfolioLink
                                                      href={"#about"}
                                                    >
                                                      {"About"}
                                                    </PortfolioLink>
                                                    <PortfolioLink
                                                      href={"#contact"}
                                                    >
                                                      {"Contact"}
                                                    </PortfolioLink>
                                                  </nav>
                                                  <PortfolioLink
                                                    className={"to-top"}
                                                    href={"#home"}
                                                  >
                                                    {"Back to top"}
                                                  </PortfolioLink>
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
                                          })()}
                                        </>
                                      );
                                    })()}
                                  </>
                                );
                              })()}
                            </>
                          );
                        })()}
                      </>
                    );
                  })()}
                </>
              );
            })()}
          </>
        );
      })()}
    </>
  );
}
