import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // Generated portfolios are served from both the root and a nested preview
  // mount (/preview/<host>/). Relative asset URLs keep the artifact portable
  // across both locations.
  base: "./",
  plugins: [react()],
});
