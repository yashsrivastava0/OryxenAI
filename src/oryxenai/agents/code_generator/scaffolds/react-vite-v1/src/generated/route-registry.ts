import type { ComponentType } from "react";

export const ROUTES = [] as const satisfies readonly {
  routeId: string;
  path: string;
  title: string;
  component: ComponentType;
}[];
