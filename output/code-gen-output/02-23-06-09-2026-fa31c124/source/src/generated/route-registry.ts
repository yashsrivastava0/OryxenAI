import type { ComponentType } from "react";

import Route0 from "../routes/home-4ea14058/index";

export const ROUTES = [
  { routeId: "home", path: "/", title: "Arjun Mehta \u2014 Senior UI/UX Designer", component: Route0 },
] as const satisfies readonly { routeId: string; path: string; title: string; component: ComponentType }[];
