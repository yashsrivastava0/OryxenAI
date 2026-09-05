import clsx, { type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Compose conditional classes and safely merge Tailwind conflicts. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
