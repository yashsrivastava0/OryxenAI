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
export function EditorialForest({ c, d }: TemplateValues) {
  const hero = c.hero;
  const eyebrow = [hero.eyebrow_primary, hero.eyebrow_secondary].filter(
    Boolean,
  );
  const headline_prefix = hero.headline_prefix;
  const headline_emphasis = hero.headline_emphasis;
  const systems = c.systems_practice;
  const capabilities = c.technical_capabilities;
  const context = c.professional_context;
  const connect = c.connect;
  return (
    <>
      <PortfolioLink className={"skip-link"} href={"#home"}>
        {"Skip to main content"}
      </PortfolioLink>
      {"\n"}
      <div className={"reading-progress"} aria-hidden={"true"}></div>
      {"\n"}
      <div className={"grain"} aria-hidden={"true"}></div>
      {"\n"}
      <PortfolioNav className={"site-nav"} aria-label={"Portfolio sections"}>
        {"\n  "}
        <div className={"site-nav__inner"}>
          {"\n    "}
          <PortfolioLink className={"wordmark"} href={"#home"}>
            {"\n      "}
            <span className={"wordmark__monogram"} aria-hidden={"true"}>
              {d.monogram}
            </span>
            {"\n      "}
            <span className={"wordmark__name"}>{hero.name}</span>
            {"\n    "}
          </PortfolioLink>
          {"\n    "}
          <ul className={"site-nav__links"}>
            {"\n"}
            {d.nav.map((item: any, index: number, items: any[]) => {
              const loop = {
                index0: index,
                index: index + 1,
                last: index === items.length - 1,
                first: index === 0,
              };
              return (
                <Fragment key={index}>
                  {"\n      "}
                  <li>
                    <PortfolioLink href={"" + "#" + item.id}>
                      <span className={"site-nav__index"} aria-hidden={"true"}>
                        {item.index}
                      </span>
                      <span>{item.label}</span>
                    </PortfolioLink>
                  </li>
                  {"\n"}
                </Fragment>
              );
            })}
            {"\n    "}
          </ul>
          {"\n  "}
        </div>
        {"\n"}
      </PortfolioNav>
      {"\n"}
      <main>
        {"\n  "}
        <header className={"hero"} id={"home"} tabIndex={Number("-1")}>
          {"\n    "}
          <div className={"container hero__grid"}>
            {"\n      "}
            <div className={"hero__copy"}>
              {"\n"}
              {truthy(eyebrow) ? (
                <>
                  {"\n        "}
                  <p className={"eyebrow hero__eyebrow"}>
                    {eyebrow[0]}
                    {truthy(eyebrow.length > 1) ? (
                      <>
                        {" "}
                        <span aria-hidden={"true"}>{"·"}</span> {eyebrow[1]}
                      </>
                    ) : null}
                  </p>
                  {"\n"}
                </>
              ) : null}
              {"\n        "}
              <ThemeElement as="h1">{hero.name}</ThemeElement>
              {"\n"}
              {truthy(
                truthy(headline_prefix) ? headline_prefix : headline_emphasis,
              ) ? (
                <>
                  {"\n        "}
                  <p className={"hero__headline"}>
                    {headline_prefix}
                    {truthy(
                      truthy(headline_prefix)
                        ? headline_emphasis
                        : headline_prefix,
                    ) ? (
                      <> </>
                    ) : null}
                    {truthy(headline_emphasis) ? (
                      <>
                        <em>{headline_emphasis}</em>
                      </>
                    ) : null}
                  </p>
                  {"\n"}
                </>
              ) : null}
              {"\n        "}
              <p className={"hero__intro"}>{hero.intro}</p>
              {"\n"}
              {truthy(hero.location) ? (
                <>
                  {"\n        "}
                  <p className={"hero__location"}>
                    <span className={"eyebrow"}>{"Location"}</span>
                    <span>{hero.location}</span>
                  </p>
                  {"\n"}
                </>
              ) : null}
              {"\n"}
              {truthy(
                truthy(hero.primary_cta_label)
                  ? hero.primary_cta_label
                  : hero.secondary_cta_label,
              ) ? (
                <>
                  {"\n        "}
                  <div className={"hero__actions"}>
                    {"\n"}
                    {truthy(hero.primary_cta_label) ? (
                      <>
                        {"\n          "}
                        <PortfolioLink
                          className={"button button--primary"}
                          href={"#systems-practice"}
                        >
                          <span className={"button__label"}>
                            {hero.primary_cta_label}
                          </span>
                          <span
                            className={"button__arrow"}
                            aria-hidden={"true"}
                          >
                            {"↓"}
                          </span>
                        </PortfolioLink>
                        {"\n"}
                      </>
                    ) : null}
                    {"\n"}
                    {truthy(hero.secondary_cta_label) ? (
                      <>
                        {"\n          "}
                        <PortfolioLink
                          className={"text-link"}
                          href={"#connect"}
                        >
                          {hero.secondary_cta_label}{" "}
                          <span aria-hidden={"true"}>{"↗"}</span>
                        </PortfolioLink>
                        {"\n"}
                      </>
                    ) : null}
                    {"\n        "}
                  </div>
                  {"\n"}
                </>
              ) : null}
              {"\n      "}
            </div>
            {"\n      "}
            <figure className={"hero__visual"} aria-hidden={"true"}>
              {"\n        "}
              <img
                src={d.hero_asset}
                width={"800"}
                height={"1200"}
                alt={""}
                decoding={"async"}
                fetchPriority={"high"}
              />
              {"\n        "}
              <span className={"hero__badge"} aria-hidden={"true"}>
                {d.monogram}
              </span>
              {"\n      "}
            </figure>
            {"\n    "}
          </div>
          {"\n    "}
          <div className={"hero__scroll-cue"} aria-hidden={"true"}>
            <span className={"hero__scroll-cue-line"}></span>
            <span>{"Scroll"}</span>
          </div>
          {"\n  "}
        </header>
        {"\n"}
        {truthy(d.marquee) ? (
          <>
            {"\n  "}
            <ThemeElement as="div" className={"marquee"} aria-hidden={"true"}>
              <div className={"marquee__track"}>
                {"\n"}
                {range(2).map((_: any, index: number, items: any[]) => {
                  const loop = {
                    index0: index,
                    index: index + 1,
                    last: index === items.length - 1,
                    first: index === 0,
                  };
                  return (
                    <Fragment key={index}>
                      {"\n    "}
                      <ul className={"marquee__list"}>
                        {d.marquee["items"].map(
                          (item: any, index: number, items: any[]) => {
                            const loop = {
                              index0: index,
                              index: index + 1,
                              last: index === items.length - 1,
                              first: index === 0,
                            };
                            return (
                              <Fragment key={index}>
                                <li>{item}</li>
                              </Fragment>
                            );
                          },
                        )}
                      </ul>
                      {"\n"}
                    </Fragment>
                  );
                })}
                {"\n  "}
              </div>
            </ThemeElement>
            {"\n"}
          </>
        ) : null}
        {"\n  "}
        <section
          className={"scene scene--systems"}
          id={"systems-practice"}
          tabIndex={Number("-1")}
          aria-labelledby={"systems-title"}
        >
          {"\n    "}
          <div className={"container"}>
            {"\n      "}
            <div className={"section-heading section-heading--wide"}>
              {"\n        "}
              <p className={"eyebrow"}>{systems.eyebrow}</p>
              {"\n        "}
              <ThemeElement as="h2" id={"systems-title"}>
                {systems.heading}
              </ThemeElement>
              {"\n"}
              {truthy(systems.intro) ? (
                <>
                  {"\n        "}
                  <p className={"section-heading__intro"}>{systems.intro}</p>
                  {"\n"}
                </>
              ) : null}
              {"\n      "}
            </div>
            {"\n      "}
            <ThemeElement as="ul" className={"pillar-grid"}>
              {"\n"}
              {d.pillars.map((pillar: any, index: number, items: any[]) => {
                const loop = {
                  index0: index,
                  index: index + 1,
                  last: index === items.length - 1,
                  first: index === 0,
                };
                return (
                  <Fragment key={index}>
                    {"\n        "}
                    <ThemeElement
                      as="li"
                      className={"pillar"}
                      data-index={pillar.index}
                    >
                      <span className={"pillar__index"} aria-hidden={"true"}>
                        {pillar.index}
                      </span>
                      <h3>{pillar.title}</h3>
                      <p>{pillar.description}</p>
                    </ThemeElement>
                    {"\n"}
                  </Fragment>
                );
              })}
              {"\n      "}
            </ThemeElement>
            {"\n    "}
          </div>
          {"\n  "}
        </section>
        {"\n  "}
        <section
          className={"scene scene--capabilities"}
          id={"technical-capabilities"}
          tabIndex={Number("-1")}
          aria-labelledby={"capabilities-title"}
        >
          {"\n    "}
          <div className={"container"}>
            {"\n      "}
            <div className={"section-heading section-heading--wide"}>
              {"\n        "}
              <p className={"eyebrow"}>{capabilities.eyebrow}</p>
              {"\n        "}
              <ThemeElement as="h2" id={"capabilities-title"}>
                {capabilities.heading}
              </ThemeElement>
              {"\n"}
              {truthy(capabilities.intro) ? (
                <>
                  {"\n        "}
                  <p className={"section-heading__intro"}>
                    {capabilities.intro}
                  </p>
                  {"\n"}
                </>
              ) : null}
              {"\n      "}
            </div>
            {"\n      "}
            <div className={"inventory-grid"}>
              {"\n"}
              {d.groups.map((group: any, index: number, items: any[]) => {
                const loop = {
                  index0: index,
                  index: index + 1,
                  last: index === items.length - 1,
                  first: index === 0,
                };
                return (
                  <Fragment key={index}>
                    {"\n        "}
                    <ThemeElement
                      as="details"
                      className={"capability-group"}
                      {...(truthy(group.open) ? { open: true } : {})}
                    >
                      {"\n          "}
                      <summary>
                        <span className={"capability-group__content"}>
                          <span className={"capability-group__heading"}>
                            <span
                              className={"capability-group__index"}
                              aria-hidden={"true"}
                            >
                              {group.index}
                            </span>
                            <span>{group.heading}</span>
                          </span>
                        </span>
                        <span
                          className={"disclosure-icon"}
                          aria-hidden={"true"}
                        ></span>
                      </summary>
                      {"\n          "}
                      <ul className={"capability-list"}>
                        {group["items"].map(
                          (item: any, index: number, items: any[]) => {
                            const loop = {
                              index0: index,
                              index: index + 1,
                              last: index === items.length - 1,
                              first: index === 0,
                            };
                            return (
                              <Fragment key={index}>
                                <li>{item}</li>
                              </Fragment>
                            );
                          },
                        )}
                      </ul>
                      {"\n        "}
                    </ThemeElement>
                    {"\n"}
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
          className={"scene scene--context"}
          id={"professional-context"}
          tabIndex={Number("-1")}
          aria-labelledby={"context-title"}
        >
          {"\n    "}
          <div className={"container context-layout"}>
            {"\n      "}
            <div className={"section-heading"}>
              {"\n        "}
              <p className={"eyebrow"}>{context.eyebrow}</p>
              {"\n        "}
              <ThemeElement as="h2" id={"context-title"}>
                {context.heading}
              </ThemeElement>
              {"\n      "}
            </div>
            {"\n      "}
            <div className={"context-content"}>
              {"\n"}
              {truthy(context.intro) ? (
                <>
                  {"\n        "}
                  <p className={"context-content__intro"}>{context.intro}</p>
                  {"\n"}
                </>
              ) : null}
              {"\n"}
              {truthy(d.organizations) ? (
                <>
                  {"\n        "}
                  <ul className={"organization-list"}>
                    {d.organizations.map(
                      (organization: any, index: number, items: any[]) => {
                        const loop = {
                          index0: index,
                          index: index + 1,
                          last: index === items.length - 1,
                          first: index === 0,
                        };
                        return (
                          <Fragment key={index}>
                            <li>{organization}</li>
                          </Fragment>
                        );
                      },
                    )}
                  </ul>
                  {"\n"}
                </>
              ) : null}
              {"\n      "}
            </div>
            {"\n    "}
          </div>
          {"\n  "}
        </section>
        {"\n  "}
        <section
          className={"scene scene--connect"}
          id={"connect"}
          tabIndex={Number("-1")}
          aria-labelledby={"connect-title"}
        >
          {"\n    "}
          <div className={"container connect-layout"}>
            {"\n      "}
            <div className={"connect-copy"}>
              {"\n        "}
              <p className={"eyebrow"}>{connect.eyebrow}</p>
              {"\n        "}
              <ThemeElement as="h2" id={"connect-title"}>
                {connect.heading}
              </ThemeElement>
              {"\n"}
              {truthy(connect.intro) ? (
                <>
                  {"\n        "}
                  <p>{connect.intro}</p>
                  {"\n"}
                </>
              ) : null}
              {"\n      "}
            </div>
            {"\n"}
            {truthy(d.destinations) ? (
              <>
                {"\n      "}
                <ul className={"destination-list"}>
                  {"\n"}
                  {d.destinations.map(
                    (destination: any, index: number, items: any[]) => {
                      const loop = {
                        index0: index,
                        index: index + 1,
                        last: index === items.length - 1,
                        first: index === 0,
                      };
                      return (
                        <Fragment key={index}>
                          {"\n        "}
                          <li
                            {...(truthy(destination.featured)
                              ? { className: "destination-list__featured" }
                              : {})}
                          >
                            <PortfolioLink
                              href={destination.url}
                              {...(truthy(destination.new_tab)
                                ? {
                                    target: "_blank",
                                    rel: "noopener noreferrer",
                                  }
                                : {})}
                            >
                              <span>{destination.label}</span>
                              <span
                                className={"destination-arrow"}
                                aria-hidden={"true"}
                              >
                                {"↗"}
                              </span>
                            </PortfolioLink>
                          </li>
                          {"\n"}
                        </Fragment>
                      );
                    },
                  )}
                  {"\n      "}
                </ul>
                {"\n"}
              </>
            ) : null}
            {"\n    "}
          </div>
          {"\n  "}
        </section>
        {"\n"}
      </main>
      {"\n"}
      <footer className={"site-footer"}>
        <div className={"container site-footer__inner"}>
          {"\n  "}
          <p>
            {hero.name}
            {truthy(hero.location) ? (
              <>
                {" "}
                <span aria-hidden={"true"}>{"·"}</span> {hero.location}
              </>
            ) : null}
          </p>
          {"\n  "}
          <PortfolioLink href={"#home"}>
            {"Back to top "}
            <span aria-hidden={"true"}>{"↑"}</span>
          </PortfolioLink>
          {"\n"}
        </div>
      </footer>
      {"\n"}
    </>
  );
}
