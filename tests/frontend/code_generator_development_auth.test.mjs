import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { bootCodeGeneratorDevelopment } from "../../src/oryxenai/web/static/code-generator-development.js";

test("developer code generator requires the shared authorized request boundary", async () => {
  const source = await readFile(
    new URL("../../src/oryxenai/web/static/code-generator-development.js", import.meta.url),
    "utf8",
  );
  assert.match(source, /export async function bootCodeGeneratorDevelopment/);
  assert.doesNotMatch(source, /\bfetch\s*\(/);
  await assert.rejects(
    bootCodeGeneratorDevelopment(),
    /authorized request function is required/,
  );
});
