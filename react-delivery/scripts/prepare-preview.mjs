// Development fixture only. Exported projects already contain their own assets.
import { cp, mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const data = JSON.parse(
  await readFile(path.join(root, "portfolio.json"), "utf8"),
);
if (!/^[a-z-]+\/v[0-9]+$/.test(data.theme_id))
  throw new Error("Invalid fixture theme.");
const source = path.resolve(
  root,
  "../src/oryxenai/themes",
  data.theme_id.replaceAll("-", "_"),
);
const manifest = JSON.parse(
  await readFile(path.join(source, "manifest.json"), "utf8"),
);
for (const file of manifest.files) {
  if (file.path.endsWith(".js") || file.path.endsWith(".html")) continue;
  if (
    file.path.split("/").some((p) => p === ".." || p === "." || !p) ||
    file.path.includes("\\")
  )
    throw new Error("Invalid theme asset path.");
  const target = path.join(root, "public/theme", file.path);
  await mkdir(path.dirname(target), { recursive: true });
  await cp(path.join(source, file.path), target);
}
