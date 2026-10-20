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
export function CobaltClassic({ c, d }: TemplateValues) {
  return (
    <>
      <PortfolioLink className={"atlas-skip"} href={"#top"}>
        {"Skip to content"}
      </PortfolioLink>
      {"\n"}
      <div className={"atlas-progress"} aria-hidden={"true"}></div>
      {"\n"}
      <aside className={"atlas-spine"} aria-label={"Portfolio"}>
        {"\n  "}
        <PortfolioLink
          className={"atlas-spine__mark"}
          href={"#top"}
          aria-label={"Back to top"}
        >
          {d.monogram}
        </PortfolioLink>
        {"\n  "}
        <span className={"atlas-spine__middle"} aria-hidden={"true"}>
          {"Portfolio"}
        </span>
        {"\n"}
      </aside>
      {"\n"}
      <div className={"atlas-shell"}>
        {"\n  "}
        <header className={"atlas-header"}>
          {"\n    "}
          <nav
            className={"atlas-wrap atlas-header__inner"}
            aria-label={"Portfolio"}
          >
            {"\n      "}
            <PortfolioLink className={"atlas-header__brand"} href={"#top"}>
              {d.monogram}
            </PortfolioLink>
            {"\n      "}
            <div className={"atlas-header__links"}>
              {"\n        "}
              <PortfolioLink href={"#practice"}>{"Practice"}</PortfolioLink>
              <PortfolioLink href={"#capabilities"}>
                {"Capabilities"}
              </PortfolioLink>
              <PortfolioLink href={"#about"}>{"About"}</PortfolioLink>
              <PortfolioLink href={"#contact"}>{"Contact"}</PortfolioLink>
              {"\n      "}
            </div>
            {"\n    "}
          </nav>
          {"\n  "}
        </header>
        {"\n  "}
        <main id={"main"}>
          {"\n    "}
          <section
            className={"atlas-intro"}
            id={"top"}
            aria-labelledby={"hero-title"}
          >
            {"\n      "}
            <div className={"atlas-wrap atlas-intro__layout"}>
              {"\n        "}
              <div className={"atlas-intro__copy"}>
                {"\n          "}
                {truthy(c.hero.eyebrow_primary) ? (
                  <>
                    <p
                      className={"atlas-small-title"}
                      data-field={"hero.eyebrow_primary"}
                    >
                      {c.hero.eyebrow_primary}
                    </p>
                  </>
                ) : null}
                {"\n          "}
                {truthy(c.hero.eyebrow_secondary) ? (
                  <>
                    <p
                      className={"atlas-small-title"}
                      data-field={"hero.eyebrow_secondary"}
                    >
                      {c.hero.eyebrow_secondary}
                    </p>
                  </>
                ) : null}
                {"\n          "}
                <ThemeElement
                  as="h1"
                  id={"hero-title"}
                  data-field={"hero.name"}
                >
                  {c.hero.name}
                </ThemeElement>
                {"\n          "}
                <p className={"atlas-intro__statement"}>
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
                {"\n          "}
                {truthy(c.hero.intro) ? (
                  <>
                    <p
                      className={"atlas-intro__lede"}
                      data-field={"hero.intro"}
                    >
                      {c.hero.intro}
                    </p>
                  </>
                ) : null}
                {"\n          "}
                {truthy(c.hero.location) ? (
                  <>
                    <p
                      className={"atlas-small-title"}
                      data-field={"hero.location"}
                    >
                      {c.hero.location}
                    </p>
                  </>
                ) : null}
                {"\n          "}
                <div className={"atlas-intro__bottom"}>
                  {"\n            "}
                  {truthy(c.hero.primary_cta_label) ? (
                    <>
                      <PortfolioLink
                        className={"atlas-pill"}
                        href={"#practice"}
                      >
                        <span data-field={"hero.primary_cta_label"}>
                          {c.hero.primary_cta_label}
                        </span>
                        <span
                          className={"atlas-pill__icon"}
                          aria-hidden={"true"}
                        >
                          {"↗"}
                        </span>
                      </PortfolioLink>
                    </>
                  ) : null}
                  {"\n            "}
                  {truthy(c.hero.secondary_cta_label) ? (
                    <>
                      <PortfolioLink
                        className={"atlas-inline"}
                        href={"#contact"}
                        data-field={"hero.secondary_cta_label"}
                      >
                        {c.hero.secondary_cta_label}
                      </PortfolioLink>
                    </>
                  ) : null}
                  {"\n          "}
                </div>
                {"\n        "}
              </div>
              {"\n        "}
              <div className={"atlas-intro__visual"} aria-hidden={"true"}>
                <span className={"atlas-intro__orb"}></span>
              </div>
              {"\n      "}
            </div>
            {"\n    "}
          </section>
          {"\n    "}
          <section
            className={"atlas-gallery atlas-section"}
            id={"practice"}
            aria-labelledby={"practice-title"}
          >
            {"\n      "}
            <div className={"atlas-wrap atlas-gallery__heading"}>
              {"\n        "}
              <div>
                {"\n          "}
                {truthy(c.systems_practice.eyebrow) ? (
                  <>
                    <p
                      className={"atlas-small-title"}
                      data-field={"systems_practice.eyebrow"}
                    >
                      {c.systems_practice.eyebrow}
                    </p>
                  </>
                ) : null}
                {"\n          "}
                <ThemeElement
                  as="h2"
                  className={"atlas-heading"}
                  id={"practice-title"}
                  data-field={"systems_practice.heading"}
                >
                  {c.systems_practice.heading}
                </ThemeElement>
                {"\n          "}
                {truthy(c.systems_practice.intro) ? (
                  <>
                    <p
                      className={"atlas-gallery__hint"}
                      data-field={"systems_practice.intro"}
                    >
                      {c.systems_practice.intro}
                    </p>
                  </>
                ) : null}
                {"\n        "}
              </div>
              {"\n      "}
            </div>
            {"\n      "}
            {truthy(c.marquee_keywords) ? (
              <>
                <ul className={"atlas-keywords"}>
                  {"\n        "}
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
                  {"\n      "}
                </ul>
              </>
            ) : null}
            {"\n      "}
            <div
              className={"atlas-gallery__track"}
              tabIndex={Number("0")}
              aria-label={"Practice areas"}
            >
              {"\n        "}
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
                      {"\n        "}
                      <article className={"atlas-project"}>
                        {"\n          "}
                        <div
                          className={
                            "" +
                            "atlas-art" +
                            (truthy(loop.index0 % 3 === 1)
                              ? " atlas-art--two"
                              : truthy(loop.index0 % 3 === 2)
                                ? " atlas-art--three"
                                : "")
                          }
                          aria-hidden={"true"}
                        >
                          <span className={"atlas-art__disc"}></span>
                        </div>
                        {"\n          "}
                        <div className={"atlas-project__body"}>
                          <div>
                            <span
                              className={"atlas-project__num"}
                              aria-hidden={"true"}
                            >
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
                              className={"atlas-project__type"}
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
                        </div>
                        {"\n        "}
                      </article>
                      {"\n        "}
                    </Fragment>
                  );
                },
              )}
              {"\n      "}
            </div>
            {"\n    "}
          </section>
          {"\n    "}
          <section
            className={"atlas-method atlas-section"}
            id={"capabilities"}
            aria-labelledby={"capabilities-title"}
          >
            {"\n      "}
            <div className={"atlas-wrap"}>
              {"\n        "}
              <div className={"atlas-method__header"}>
                {"\n          "}
                {truthy(c.technical_capabilities.eyebrow) ? (
                  <>
                    <p
                      className={"atlas-small-title"}
                      data-field={"technical_capabilities.eyebrow"}
                    >
                      {c.technical_capabilities.eyebrow}
                    </p>
                  </>
                ) : null}
                {"\n          "}
                <ThemeElement
                  as="h2"
                  className={"atlas-heading"}
                  id={"capabilities-title"}
                  data-field={"technical_capabilities.heading"}
                >
                  {c.technical_capabilities.heading}
                </ThemeElement>
                {"\n          "}
                {truthy(c.technical_capabilities.intro) ? (
                  <>
                    <p
                      className={"atlas-method__lede"}
                      data-field={"technical_capabilities.intro"}
                    >
                      {c.technical_capabilities.intro}
                    </p>
                  </>
                ) : null}
                {"\n        "}
              </div>
              {"\n        "}
              <div className={"atlas-capability-grid"}>
                {"\n          "}
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
                        {"\n          "}
                        {(() => {
                          const group_index = loop.index0;
                          return (
                            <>
                              {"\n          "}
                              <ThemeElement
                                as="article"
                                className={"atlas-capability-group"}
                              >
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
                                <ul>
                                  {"\n            "}
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
                                  {"\n          "}
                                </ul>
                              </ThemeElement>
                              {"\n          "}
                            </>
                          );
                        })()}
                      </Fragment>
                    );
                  },
                )}
                {"\n        "}
              </div>
              {"\n      "}
            </div>
            {"\n    "}
          </section>
          {"\n    "}
          <section
            className={"atlas-profile atlas-section"}
            id={"about"}
            aria-labelledby={"about-title"}
          >
            {"\n      "}
            <div className={"atlas-wrap atlas-profile__layout"}>
              {"\n        "}
              {truthy(c.professional_context.eyebrow) ? (
                <>
                  <p
                    className={"atlas-profile__aside"}
                    data-field={"professional_context.eyebrow"}
                  >
                    {c.professional_context.eyebrow}
                  </p>
                </>
              ) : null}
              {"\n        "}
              <div
                className={"atlas-profile__portrait"}
                aria-hidden={"true"}
              ></div>
              {"\n        "}
              <div className={"atlas-profile__copy"}>
                {"\n          "}
                <ThemeElement
                  as="h2"
                  className={"atlas-heading"}
                  id={"about-title"}
                  data-field={"professional_context.heading"}
                >
                  {c.professional_context.heading}
                </ThemeElement>
                {"\n          "}
                {truthy(c.professional_context.intro) ? (
                  <>
                    <p data-field={"professional_context.intro"}>
                      {c.professional_context.intro}
                    </p>
                  </>
                ) : null}
                {"\n          "}
                {truthy(c.professional_context.organizations) ? (
                  <>
                    <ul className={"atlas-organizations"}>
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
                {"\n        "}
              </div>
              {"\n      "}
            </div>
            {"\n    "}
          </section>
          {"\n    "}
          <section
            className={"atlas-contact"}
            id={"contact"}
            aria-labelledby={"contact-title"}
          >
            {"\n      "}
            <div className={"atlas-wrap"}>
              <div className={"atlas-contact__panel"}>
                {"\n        "}
                {truthy(c.connect.eyebrow) ? (
                  <>
                    <p
                      className={"atlas-contact__label"}
                      data-field={"connect.eyebrow"}
                    >
                      {c.connect.eyebrow}
                    </p>
                  </>
                ) : null}
                {"\n        "}
                <ThemeElement
                  as="h2"
                  id={"contact-title"}
                  data-field={"connect.heading"}
                >
                  {c.connect.heading}
                </ThemeElement>
                {"\n        "}
                {truthy(c.connect.intro) ? (
                  <>
                    <p
                      className={"atlas-contact__intro"}
                      data-field={"connect.intro"}
                    >
                      {c.connect.intro}
                    </p>
                  </>
                ) : null}
                {"\n        "}
                <div className={"atlas-destinations"}>
                  {d.destinations.map(
                    (item: any, index: number, items: any[]) => {
                      const loop = {
                        index0: index,
                        index: index + 1,
                        last: index === items.length - 1,
                        first: index === 0,
                      };
                      return (
                        <Fragment key={index}>
                          <PortfolioLink
                            className={"atlas-pill atlas-pill--white"}
                            href={item.url}
                            {...(truthy(item.external)
                              ? { target: "_blank", rel: "noopener noreferrer" }
                              : {})}
                            data-field={
                              "" +
                              "connect.destinations[" +
                              loop.index0 +
                              "].label"
                            }
                          >
                            {item.label}
                          </PortfolioLink>
                        </Fragment>
                      );
                    },
                  )}
                </div>
                {"\n      "}
              </div>
            </div>
            {"\n    "}
          </section>
          {"\n  "}
        </main>
        {"\n  "}
        <footer className={"atlas-footer"}>
          <div className={"atlas-wrap atlas-footer__inner"}>
            <PortfolioLink href={"#top"}>{"Back to top"}</PortfolioLink>
          </div>
        </footer>
        {"\n"}
      </div>
      {"\n"}
    </>
  );
}
