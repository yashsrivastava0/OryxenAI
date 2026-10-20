import type { ReactNode } from "react";
import { PortfolioLink } from "./interactive/routing";
import { ThemeElement } from "./interactive/motion";

// Inputs are projected and schema-validated by PortfolioPageContent. These
// extensible records also contain the pinned host's presentation-only values.
export type TemplateValues = { c: Record<string, any>; d: Record<string, any> };
export type Portfolio = TemplateValues & {
  schema: "ReactPortfolio/v1";
  theme_id: string;
  adapter_revision: string;
  lang: string;
  body_class: string;
  stylesheet: string;
};
export const truthy = (value: unknown): boolean =>
  Array.isArray(value)
    ? value.length > 0
    : value !== null && typeof value === "object"
      ? Object.keys(value).length > 0
      : Boolean(value);
export const range = (length: number): number[] =>
  Array.from({ length }, (_, i) => i);

export function ProjectLink({
  project,
  index,
  className,
  children,
}: {
  project: Record<string, any>;
  index: number;
  className: string;
  children: ReactNode;
}) {
  const isCase = truthy(project.problem) && truthy(project.approach);
  if (!isCase && !project.external_url)
    return (
      <ThemeElement as="div" className={className}>
        {children}
      </ThemeElement>
    );
  return (
    <PortfolioLink
      className={className}
      href={isCase ? `#case-${index}` : project.external_url}
      aria-label={isCase ? `${project.title} case study` : project.title}
      target={isCase ? undefined : "_blank"}
      rel={isCase ? undefined : "noopener noreferrer"}
    >
      {children}
    </PortfolioLink>
  );
}
