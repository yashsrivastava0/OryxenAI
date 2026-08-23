import { build } from "esbuild";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const outfile = path.join(root, "..", "static", "auth-client.js");

await build({
  entryPoints: [path.join(root, "src", "auth-client.js")],
  bundle: true,
  format: "iife",
  minify: true,
  target: "es2022",
  outfile,
});

// esbuild can emit Supabase's intentional " space/tab/newline/CR/="
// character set as a template literal containing a trailing tab. Keep the
// same runtime value while making the generated asset pass Git whitespace
// checks and remain reproducible across local builds.
const ignoredBase64Whitespace = ["`", " ", "\t", "\n", "\\r", "=", "`"].join("");
const bundle = await readFile(outfile, "utf8");
const normalizedBundle = bundle.replace(
  ignoredBase64Whitespace,
  '" \\t\\n\\r="',
);
await writeFile(outfile, normalizedBundle, "utf8");
