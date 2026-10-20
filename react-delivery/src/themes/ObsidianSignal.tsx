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
export function ObsidianSignal({ c, d }: TemplateValues) {
  return (
    <>
      <PortfolioLink className={"sg-skip"} href={"#top"}>
        {"Skip to content"}
      </PortfolioLink>
      {"\n"}
      <div
        className={"sg-progress"}
        data-css-progress={"true"}
        aria-hidden={"true"}
      ></div>
      {"\n"}
      <nav className={"sg-nav"} aria-label={"Portfolio"}>
        {"\n  "}
        <div className={"sg-container sg-nav__inner"}>
          {"\n    "}
          <PortfolioLink className={"sg-brand"} href={"#top"}>
            <span className={"sg-brand__mark"} aria-hidden={"true"}>
              {d.monogram}
            </span>
          </PortfolioLink>
          {"\n    "}
          <ul className={"sg-nav__links"}>
            <li>
              <PortfolioLink href={"#practice"}>{"Practice"}</PortfolioLink>
            </li>
            <li>
              <PortfolioLink href={"#capabilities"}>
                {"Capabilities"}
              </PortfolioLink>
            </li>
            <li>
              <PortfolioLink href={"#about"}>{"About"}</PortfolioLink>
            </li>
            <li>
              <PortfolioLink href={"#contact"}>{"Contact"}</PortfolioLink>
            </li>
          </ul>
          {"\n  "}
        </div>
        {"\n"}
      </nav>
      {"\n"}
      <main id={"main"} className={"sg-frame"}>
        {"\n  "}
        <header className={"sg-hero"} id={"top"}>
          {"\n    "}
          <div className={"sg-container sg-hero__grid"}>
            {"\n      "}
            <div className={"sg-hero__copy"}>
              {"\n        "}
              {truthy(c.hero.eyebrow_primary) ? (
                <>
                  <p
                    className={"sg-kicker"}
                    data-field={"hero.eyebrow_primary"}
                  >
                    {c.hero.eyebrow_primary}
                  </p>
                </>
              ) : null}
              {"\n        "}
              {truthy(c.hero.eyebrow_secondary) ? (
                <>
                  <p
                    className={"sg-kicker"}
                    data-field={"hero.eyebrow_secondary"}
                  >
                    {c.hero.eyebrow_secondary}
                  </p>
                </>
              ) : null}
              {"\n        "}
              <ThemeElement as="h1" data-field={"hero.name"}>
                {c.hero.name}
              </ThemeElement>
              {"\n        "}
              <p className={"sg-hero__statement"}>
                {truthy(c.hero.headline_prefix) ? (
                  <>
                    <span data-field={"hero.headline_prefix"}>
                      {c.hero.headline_prefix}
                    </span>
                  </>
                ) : null}{" "}
                {truthy(c.hero.headline_emphasis) ? (
                  <>
                    <em data-field={"hero.headline_emphasis"}>
                      {c.hero.headline_emphasis}
                    </em>
                  </>
                ) : null}
              </p>
              {"\n        "}
              {truthy(c.hero.intro) ? (
                <>
                  <p className={"sg-hero__intro"} data-field={"hero.intro"}>
                    {c.hero.intro}
                  </p>
                </>
              ) : null}
              {"\n        "}
              {truthy(c.hero.location) ? (
                <>
                  <p className={"sg-kicker"} data-field={"hero.location"}>
                    {c.hero.location}
                  </p>
                </>
              ) : null}
              {"\n        "}
              <div className={"sg-hero__actions"}>
                {"\n          "}
                {truthy(c.hero.primary_cta_label) ? (
                  <>
                    <PortfolioLink className={"sg-button"} href={"#practice"}>
                      <span data-field={"hero.primary_cta_label"}>
                        {c.hero.primary_cta_label}
                      </span>
                      <span className={"sg-button__arrow"} aria-hidden={"true"}>
                        {"↘"}
                      </span>
                    </PortfolioLink>
                  </>
                ) : null}
                {"\n          "}
                {truthy(c.hero.secondary_cta_label) ? (
                  <>
                    <PortfolioLink
                      className={"sg-text-link"}
                      href={"#contact"}
                      data-field={"hero.secondary_cta_label"}
                    >
                      {c.hero.secondary_cta_label}
                    </PortfolioLink>
                  </>
                ) : null}
                {"\n        "}
              </div>
              {"\n      "}
            </div>
            {"\n      "}
            <div className={"sg-hero__visual"} aria-hidden={"true"}>
              <span className={"sg-hero__plasma"}></span>
              <span className={"sg-hero__object"}></span>
            </div>
            {"\n    "}
          </div>
          {"\n  "}
        </header>
        {"\n  "}
        <section
          className={"sg-work sg-section"}
          id={"practice"}
          aria-labelledby={"practice-title"}
        >
          {"\n    "}
          {truthy(c.marquee_keywords) ? (
            <>
              <div className={"sg-ticker"}>
                <ul className={"sg-ticker__list"}>
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
                </ul>
              </div>
            </>
          ) : null}
          {"\n    "}
          <div className={"sg-container"}>
            {"\n      "}
            <div className={"sg-work__head"}>
              <div>
                {"\n        "}
                {truthy(c.systems_practice.eyebrow) ? (
                  <>
                    <p
                      className={"sg-section__number"}
                      data-field={"systems_practice.eyebrow"}
                    >
                      {c.systems_practice.eyebrow}
                    </p>
                  </>
                ) : null}
                {"\n        "}
                <ThemeElement
                  as="h2"
                  className={"sg-section__title"}
                  id={"practice-title"}
                  data-field={"systems_practice.heading"}
                >
                  {c.systems_practice.heading}
                </ThemeElement>
                {"\n        "}
                {truthy(c.systems_practice.intro) ? (
                  <>
                    <p
                      className={"sg-section__lede"}
                      data-field={"systems_practice.intro"}
                    >
                      {c.systems_practice.intro}
                    </p>
                  </>
                ) : null}
                {"\n      "}
              </div>
            </div>
            {"\n      "}
            {truthy(c.systems_practice.pillars) ? (
              <>
                {(() => {
                  const pillar = c.systems_practice.pillars[0];
                  return (
                    <>
                      {"\n      "}
                      <article className={"sg-project-feature"}>
                        <div
                          className={"sg-media sg-media--signal"}
                          aria-hidden={"true"}
                        ></div>
                        <div className={"sg-project-feature__copy"}>
                          <span
                            className={"sg-project__meta"}
                            aria-hidden={"true"}
                          >
                            {"Selected focus"}
                          </span>
                          <div>
                            <h3
                              className={"sg-project__title"}
                              data-field={"systems_practice.pillars[0].title"}
                            >
                              {pillar.title}
                            </h3>
                            <p
                              className={"sg-project__desc"}
                              data-field={
                                "systems_practice.pillars[0].description"
                              }
                            >
                              {pillar.description}
                            </p>
                          </div>
                        </div>
                      </article>
                      {"\n      "}
                    </>
                  );
                })()}
              </>
            ) : null}
            {"\n      "}
            <div className={"sg-project-grid"}>
              {"\n        "}
              {c.systems_practice.pillars
                .slice(1)
                .map((pillar: any, index: number, items: any[]) => {
                  const loop = {
                    index0: index,
                    index: index + 1,
                    last: index === items.length - 1,
                    first: index === 0,
                  };
                  return (
                    <Fragment key={index}>
                      {"\n        "}
                      <article className={"sg-project-row"}>
                        <div className={"sg-media"} aria-hidden={"true"}></div>
                        <div className={"sg-project-row__copy"}>
                          <div>
                            <h3
                              className={"sg-project__title"}
                              data-field={
                                "" +
                                "systems_practice.pillars[" +
                                loop.index +
                                "].title"
                              }
                            >
                              {pillar.title}
                            </h3>
                            <p
                              className={"sg-project__desc"}
                              data-field={
                                "" +
                                "systems_practice.pillars[" +
                                loop.index +
                                "].description"
                              }
                            >
                              {pillar.description}
                            </p>
                          </div>
                        </div>
                      </article>
                      {"\n        "}
                    </Fragment>
                  );
                })}
              {"\n      "}
            </div>
            {"\n    "}
          </div>
          {"\n  "}
        </section>
        {"\n  "}
        <section
          className={"sg-process sg-section"}
          id={"capabilities"}
          aria-labelledby={"capabilities-title"}
        >
          {"\n    "}
          <div className={"sg-container sg-process__layout"}>
            {"\n      "}
            <div className={"sg-process__intro"}>
              {"\n        "}
              {truthy(c.technical_capabilities.eyebrow) ? (
                <>
                  <p
                    className={"sg-section__number"}
                    data-field={"technical_capabilities.eyebrow"}
                  >
                    {c.technical_capabilities.eyebrow}
                  </p>
                </>
              ) : null}
              {"\n        "}
              <ThemeElement
                as="h2"
                className={"sg-section__title"}
                id={"capabilities-title"}
                data-field={"technical_capabilities.heading"}
              >
                {c.technical_capabilities.heading}
              </ThemeElement>
              {"\n        "}
              {truthy(c.technical_capabilities.intro) ? (
                <>
                  <p
                    className={"sg-section__lede"}
                    data-field={"technical_capabilities.intro"}
                  >
                    {c.technical_capabilities.intro}
                  </p>
                </>
              ) : null}
              {"\n      "}
            </div>
            {"\n      "}
            <div className={"sg-steps"}>
              {"\n        "}
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
                      {(() => {
                        const group_index = loop.index0;
                        return (
                          <>
                            {"\n        "}
                            <article className={"sg-step"}>
                              <span
                                className={"sg-step__index"}
                                aria-hidden={"true"}
                              >
                                {"0"}
                                {loop.index}
                              </span>
                              <div>
                                <h3
                                  data-field={
                                    "" +
                                    "technical_capabilities.groups[" +
                                    group_index +
                                    "].heading"
                                  }
                                >
                                  {group.heading}
                                </h3>
                                <ul className={"sg-capability-items"}>
                                  {group["items"].map(
                                    (
                                      item: any,
                                      index: number,
                                      items: any[],
                                    ) => {
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
                                              "" +
                                              "technical_capabilities.groups[" +
                                              group_index +
                                              "].items[" +
                                              loop.index0 +
                                              "]"
                                            }
                                          >
                                            {item}
                                          </li>
                                        </Fragment>
                                      );
                                    },
                                  )}
                                </ul>
                              </div>
                            </article>
                            {"\n        "}
                          </>
                        );
                      })()}
                    </Fragment>
                  );
                },
              )}
              {"\n      "}
            </div>
            {"\n    "}
          </div>
          {"\n  "}
        </section>
        {"\n  "}
        <section
          className={"sg-about sg-section"}
          id={"about"}
          aria-labelledby={"about-title"}
        >
          {"\n    "}
          <div className={"sg-container sg-about__layout"}>
            {"\n      "}
            <div className={"sg-about__copy"}>
              {"\n        "}
              {truthy(c.professional_context.eyebrow) ? (
                <>
                  <p
                    className={"sg-section__number"}
                    data-field={"professional_context.eyebrow"}
                  >
                    {c.professional_context.eyebrow}
                  </p>
                </>
              ) : null}
              {"\n        "}
              <ThemeElement
                as="h2"
                className={"sg-about__statement"}
                id={"about-title"}
                data-field={"professional_context.heading"}
              >
                {c.professional_context.heading}
              </ThemeElement>
              {"\n        "}
              {truthy(c.professional_context.intro) ? (
                <>
                  <p
                    className={"sg-about__body"}
                    data-field={"professional_context.intro"}
                  >
                    {c.professional_context.intro}
                  </p>
                </>
              ) : null}
              {"\n        "}
              {truthy(c.professional_context.organizations) ? (
                <>
                  <ul className={"sg-organizations"}>
                    {c.professional_context.organizations.map(
                      (item: any, index: number, items: any[]) => {
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
                                "" +
                                "professional_context.organizations[" +
                                loop.index0 +
                                "]"
                              }
                            >
                              {item}
                            </li>
                          </Fragment>
                        );
                      },
                    )}
                  </ul>
                </>
              ) : null}
              {"\n      "}
            </div>
            {"\n      "}
            <div className={"sg-about__aside"}>
              <div className={"sg-portrait"} aria-hidden={"true"}></div>
            </div>
            {"\n    "}
          </div>
          {"\n  "}
        </section>
        {"\n  "}
        <section
          className={"sg-contact sg-section"}
          id={"contact"}
          aria-labelledby={"contact-title"}
        >
          {"\n    "}
          <div className={"sg-container sg-contact__layout"}>
            {"\n      "}
            {truthy(c.connect.eyebrow) ? (
              <>
                <p
                  className={"sg-section__number"}
                  data-field={"connect.eyebrow"}
                >
                  {c.connect.eyebrow}
                </p>
              </>
            ) : null}
            {"\n      "}
            <ThemeElement
              as="h2"
              id={"contact-title"}
              data-field={"connect.heading"}
            >
              {c.connect.heading}
            </ThemeElement>
            {"\n      "}
            {truthy(c.connect.intro) ? (
              <>
                <p className={"sg-section__lede"} data-field={"connect.intro"}>
                  {c.connect.intro}
                </p>
              </>
            ) : null}
            {"\n      "}
            <div className={"sg-contact__actions"}>
              {d.destinations.map((item: any, index: number, items: any[]) => {
                const loop = {
                  index0: index,
                  index: index + 1,
                  last: index === items.length - 1,
                  first: index === 0,
                };
                return (
                  <Fragment key={index}>
                    <PortfolioLink
                      className={"sg-button"}
                      href={item.url}
                      {...(truthy(item.external)
                        ? { target: "_blank", rel: "noopener noreferrer" }
                        : {})}
                      data-field={
                        "" + "connect.destinations[" + loop.index0 + "].label"
                      }
                    >
                      {item.label}
                    </PortfolioLink>
                  </Fragment>
                );
              })}
            </div>
            {"\n    "}
          </div>
          {"\n  "}
        </section>
        {"\n"}
      </main>
      {"\n"}
      <footer className={"sg-footer"}>
        <div className={"sg-container sg-footer__bottom"}>
          <PortfolioLink href={"#top"}>{"Back to top"}</PortfolioLink>
        </div>
      </footer>
      {"\n"}
    </>
  );
}
