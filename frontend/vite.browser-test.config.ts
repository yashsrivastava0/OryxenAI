import { defineConfig } from "vite";
import preact from "@preact/preset-vite";

export default defineConfig({
  root: "browser-test",
  plugins: [preact()],
  server: { host: "127.0.0.1", port: 4178, strictPort: true },
});
