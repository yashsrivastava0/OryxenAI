import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  // Generated portfolios are served from both the root and a nested preview
  // mount (/preview/<host>/). Relative asset URLs keep the artifact portable
  // across both locations.
  base: "./",
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  plugins: [react()],
});
