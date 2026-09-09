import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("preview controllers initialize on iframe load without ready/init recursion", async () => {
  const [developer, product] = await Promise.all([
    readFile(
      new URL("../../src/oryxenai/web/static/code-generator-development.js", import.meta.url),
      "utf8",
    ),
    readFile(
      new URL("../../frontend/src/stages/generation/GenerationStage.tsx", import.meta.url),
      "utf8",
    ),
  ]);

  assert.match(developer, /previewFrame\.addEventListener\('load',[\s\S]*sendPreviewInit\(\)/);
  assert.match(product, /onLoad=\{sendPreviewInit\}/);
  assert.doesNotMatch(
    developer,
    /preview:ready[\s\S]{0,500}sendPreviewInit\(\)/,
  );
  assert.doesNotMatch(
    product,
    /data\?\.type === ["']preview:ready[\s\S]{0,500}sendPreviewInit\(\)/,
  );
});
