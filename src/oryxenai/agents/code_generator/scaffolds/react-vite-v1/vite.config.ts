import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  // Generated portfolios are served from both the root and a nested preview
  // mount (/preview/<host>/). Relative asset URLs keep the artifact portable
  // across both locations.
  base: "./",
  resolve: {
    alias: {
      // process.cwd() is the disposable candidate root. Resolving from it is
      // stable on Windows nested workspaces where esbuild cannot safely walk
      // a file URL parent chain.
      "@": resolve(process.cwd(), "src"),
    },
  },
  plugins: [react()],
});
