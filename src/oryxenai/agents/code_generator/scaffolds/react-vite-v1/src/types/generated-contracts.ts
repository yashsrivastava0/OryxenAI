import type { ComponentType } from "react";

export type GeneratedRoute = { routeId: string; path: string; title: string };

export type RegisteredRoute = GeneratedRoute & { component: ComponentType };
