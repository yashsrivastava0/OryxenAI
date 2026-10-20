import { build } from "esbuild";
import { createHash } from "node:crypto";
import { cp, mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { execFileSync } from "node:child_process";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const destination = path.resolve(root, "../src/oryxenai/delivery/templates");
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
execFileSync(
  process.execPath,
  [path.join(root, "node_modules/typescript/bin/tsc"), "--noEmit"],
  { cwd: root, stdio: "inherit" },
);
await mkdir(destination, { recursive: true });
await build({
  entryPoints: [path.join(root, "tests/render.tsx")],
  bundle: true,
  platform: "node",
  format: "cjs",
  target: "node22",
  outfile: path.join(root, "../.workspace/react-tests/render.cjs"),
});
await build({
  entryPoints: [path.join(root, "tests/browser.tsx")],
  bundle: true,
  minify: true,
  format: "esm",
  target: "es2022",
  outfile: path.join(root, "../.workspace/react-tests/browser.js"),
});
await build({
  entryPoints: [path.join(root, "tests/app-host.ts")],
  bundle: true,
  minify: true,
  format: "esm",
  target: "es2022",
  outfile: path.join(root, "../.workspace/react-tests/app-host.js"),
});
const entries = [];
async function collect(folder) {
  for (const entry of await readdir(path.join(root, folder), {
    withFileTypes: true,
  })) {
    const relative = path.posix.join(folder, entry.name);
    if (entry.isDirectory()) await collect(relative);
    else if (!relative.endsWith("viewer.tsx")) entries.push(relative);
  }
}
await collect("src");
entries.push("tsconfig.json", "index.html", "vite.config.ts");
const files = {};
for (const relative of entries.sort()) {
  const data = await readFile(path.join(root, relative));
  await mkdir(path.dirname(path.join(destination, relative)), {
    recursive: true,
  });
  await cp(path.join(root, relative), path.join(destination, relative));
  files[relative] = hash(data);
}
for (const relative of ["package.json", "package-lock.json"]) {
  const source = path.join(root, "project", relative);
  await cp(source, path.join(destination, relative));
  files[relative] = hash(await readFile(source));
}
const viewer = await build({
  entryPoints: [path.join(root, "src/viewer.tsx")],
  bundle: true,
  write: false,
  minify: true,
  format: "esm",
  target: "es2022",
  outfile: "viewer.js",
});
const javascript = viewer.outputFiles
  .find((file) => file.path.endsWith(".js"))
  .text.replace(/<\/script/gi, "<\\/script");
const css =
  viewer.outputFiles.find((file) => file.path.endsWith(".css"))?.text ?? "";
await writeFile(
  path.join(destination, "viewer.html"),
  `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>${css}</style></head><body><div id="root"></div><script type="module">${javascript}</script></body></html>`,
);
await writeFile(
  path.join(destination, "template-manifest.json"),
  JSON.stringify(
    {
      schema: "ReactTemplates/v1",
      adapter_revision: "1",
      files,
      adapter_sources_sha256: hash(JSON.stringify(files)),
      checks: {
        typescript: "passed",
        viewer_bundle: "passed",
        browser: "requires_ci_fixture_checks",
      },
    },
    null,
    2,
  ) + "\n",
);
console.log("React delivery templates and MCP viewer built.");
