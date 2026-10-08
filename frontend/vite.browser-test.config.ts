import { defineConfig } from "vite";
import preact from "@preact/preset-vite";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const catalogModule = "virtual:theme-catalog";
const catalog = execFileSync("uv", ["run", "--no-sync", "python", "-c", "import json; from oryxenai.agents.discovery.palette import palette_question; print(json.dumps(palette_question().model_dump(mode='json')))"] , {
  cwd: fileURLToPath(new URL("..", import.meta.url)),
  encoding: "utf-8",
});

export default defineConfig({
  root: "browser-test",
  plugins: [preact(), {
    name: "theme-catalog-fixture",
    resolveId(id) { if (id === catalogModule) return "\0" + catalogModule; },
    load(id) { if (id === "\0" + catalogModule) return `export default ${catalog}`; },
  }],
  server: {
    host: "127.0.0.1",
    port: 4178,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
