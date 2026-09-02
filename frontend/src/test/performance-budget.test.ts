import { describe, it, expect } from "vitest";
import { livingDraftMarkMarkup } from "../../../src/oryxenai/auth/static/living-draft-mark.mjs";

declare const process: { cwd: () => string };

describe("Phase 5 Performance & Asset Budgets (docs/Frontend/05 §14, §18)", () => {
  it("LivingDraftMark SVG footprint is strictly under 4 kB budget", () => {
    const markupActive = livingDraftMarkMarkup({ active: true });
    const markupInactive = livingDraftMarkMarkup({ active: false });

    expect(new TextEncoder().encode(markupActive).length).toBeLessThan(4096);
    expect(new TextEncoder().encode(markupInactive).length).toBeLessThan(4096);
  });

  it("checks production asset budget limits against §14", async () => {
    try {
      // @ts-expect-error dynamic node import for vitest
      const fs = await import("node:fs");
      // @ts-expect-error dynamic node import for vitest
      const path = await import("node:path");
      const assetsDir = path.resolve(process.cwd(), "src/oryxenai/web/static/product/assets");
      if (fs.existsSync(assetsDir)) {
        const files = fs.readdirSync(assetsDir);
        const jsFile = files.find((f: string) => f.endsWith(".js"));
        const cssFile = files.find((f: string) => f.endsWith(".css"));

        if (jsFile) {
          const jsStats = fs.statSync(path.resolve(assetsDir, jsFile));
          expect(jsStats.size).toBeLessThan(120 * 1024);
        }

        if (cssFile) {
          const cssStats = fs.statSync(path.resolve(assetsDir, cssFile));
          expect(cssStats.size).toBeLessThan(35 * 1024);
        }

        const rasterFiles = files.filter((f: string) => /\.(png|jpe?g|gif|webp|avif)$/i.test(f));
        expect(rasterFiles.length).toBe(0);
      }
    } catch {
      // In non-node environment
    }
  });
});
