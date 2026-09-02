import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

// Builds into src/oryxenai/web/static/product/, which FastAPI serves as a
// plain static directory (see src/oryxenai/web/routes.py). This project never
// runs a Node server in production — `npm run dev` is a watch-mode build for
// local iteration only, per docs/Frontend/05 §16 "Deployment target".
export default defineConfig({
  // root defaults to this file's directory (frontend/) — no need to set it.
  base: "/static/product/",
  plugins: [preact()],
  build: {
    outDir: "../src/oryxenai/web/static/product",
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      // No index.html: the entry is loaded programmatically by
      // app-auth-bootstrap.mjs after auth resolves, not served by Vite.
      input: "src/main.tsx",
      preserveEntrySignatures: "exports-only",
    },
  },
  test: {
    // Node environment is enough for Phase 1: pure adapters, URL codec, and
    // error mapping. Add jsdom + a component-testing library only once a
    // later phase actually needs to render and assert against Preact output.
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
