import { App } from "@modelcontextprotocol/ext-apps";
import { createRoot } from "react-dom/client";
import { PortfolioApp } from "./PortfolioApp";
import type { Portfolio } from "./template-values";

const app = new App(
  { name: "OryxenAI React portfolio", version: "1.0.0" },
  {},
  { autoResize: true },
);
const root = createRoot(document.getElementById("root")!);
let generation = 0;
let revoke: Array<() => void> = [];

type Entry = { path: string; bytes: number; sha256: string };
const digest = async (bytes: Uint8Array) =>
  Array.from(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", bytes as Uint8Array<ArrayBuffer>),
    ),
    (b) => b.toString(16).padStart(2, "0"),
  ).join("");
async function read(
  link: string,
  entry: Entry,
  current: number,
): Promise<Uint8Array<ArrayBuffer>> {
  const bytes = new Uint8Array(entry.bytes);
  let cursor = 0;
  do {
    if (generation !== current) throw new Error("Preview replaced.");
    const reply = await app.callServerTool({
      name: "read_preview_asset",
      arguments: { share_link: link, path: entry.path, cursor },
    });
    const chunk = reply.structuredContent as Record<string, any>;
    if (reply.isError || !chunk || chunk.error)
      throw new Error(chunk?.error?.message ?? "This preview is unavailable.");
    const data = Uint8Array.from(atob(chunk.data), (char) =>
      char.charCodeAt(0),
    );
    if (
      chunk.offset !== cursor ||
      cursor + data.length > bytes.length ||
      (await digest(data)) !== chunk.chunk_sha256
    )
      throw new Error("Preview asset integrity check failed.");
    bytes.set(data, cursor);
    cursor += data.length;
    if (chunk.next_cursor === null) break;
    if (chunk.next_cursor !== cursor || !data.length)
      throw new Error("Invalid asset cursor.");
  } while (cursor < bytes.length);
  if (cursor !== entry.bytes || (await digest(bytes)) !== entry.sha256)
    throw new Error("Preview asset integrity check failed.");
  return bytes;
}

app.ontoolresult = async (result) => {
  const current = ++generation;
  revoke.forEach((close) => close());
  revoke = [];
  const owned = revoke;
  const meta = result._meta as
    | { share_link?: string; manifest?: { files: Entry[]; expires_at: string } }
    | undefined;
  if (!meta?.share_link || !meta.manifest) {
    root.render(
      <p role="alert">
        This host did not provide the portfolio view. Import the React project
        in a coding client.
      </p>,
    );
    return;
  }
  root.render(<p role="status">Opening React portfolio…</p>);
  try {
    const link = meta.share_link;
    const files = meta.manifest.files;
    const data = files.find((file) => file.path === "portfolio.json");
    if (!data) throw new Error("Portfolio data is unavailable.");
    const portfolio = JSON.parse(
      new TextDecoder().decode(await read(link, data, current)),
    ) as Portfolio;
    if (
      portfolio.schema !== "ReactPortfolio/v1" ||
      portfolio.adapter_revision !== "1"
    )
      throw new Error(
        "This viewer does not support the shared adapter revision.",
      );
    const assets = new Map<string, string>();
    // App calls keep binary font/image transfer outside the model's context.
    for (const file of files.filter(
      (f) =>
        f.path.startsWith("public/theme/") &&
        /\.(woff2?|svg|png|jpe?g|webp)$/.test(f.path),
    )) {
      const bytes = await read(link, file, current);
      if (generation !== current) throw new Error("Preview replaced.");
      const mime = file.path.endsWith(".woff2")
        ? "font/woff2"
        : file.path.endsWith(".svg")
          ? "image/svg+xml"
          : file.path.endsWith(".png")
            ? "image/png"
            : /\.jpe?g$/.test(file.path)
              ? "image/jpeg"
              : file.path.endsWith(".webp")
                ? "image/webp"
                : "font/woff";
      const url = URL.createObjectURL(new Blob([bytes], { type: mime }));
      assets.set(file.path.slice("public/theme/".length), url);
      owned.push(() => URL.revokeObjectURL(url));
    }
    const stylesheet = files.find(
      (f) => "./" + f.path.slice("public/".length) === portfolio.stylesheet,
    );
    if (!stylesheet)
      throw new Error("The portfolio stylesheet is unavailable.");
    const css = new TextDecoder()
      .decode(await read(link, stylesheet, current))
      .replace(/url\(\s*['"]?([^)'"\s]+)['"]?\s*\)/g, (whole, path: string) => {
        const normalized = new URL(
          path,
          "https://theme.invalid/" +
            stylesheet.path.slice("public/theme/".length),
        ).pathname.slice(1);
        return assets.has(normalized)
          ? `url("${assets.get(normalized)}")`
          : whole;
      });
    if (generation !== current) throw new Error("Preview replaced.");
    const style = document.createElement("style");
    style.textContent = css;
    document.head.append(style);
    owned.push(() => style.remove());
    if (portfolio.d.hero_asset)
      portfolio.d.hero_asset = assets.get(
        String(portfolio.d.hero_asset).replace("./theme/", ""),
      );
    if (generation !== current) return;
    root.render(<PortfolioApp portfolio={portfolio} />);
    const remaining = Date.parse(meta.manifest.expires_at) - Date.now();
    const timeout = window.setTimeout(
      () => {
        ++generation;
        root.render(
          <p role="status">
            This handoff has expired. Ask its owner for a new link.
          </p>,
        );
        revoke.forEach((close) => close());
        revoke = [];
      },
      Math.max(0, remaining),
    );
    revoke.push(() => clearTimeout(timeout));
  } catch (error) {
    owned.splice(0).forEach((close) => close());
    if (generation === current)
      root.render(
        <p role="alert">
          {error instanceof Error
            ? error.message
            : "The portfolio could not be opened."}
        </p>,
      );
  }
};
app.onteardown = async () => {
  ++generation;
  root.unmount();
  revoke.forEach((close) => close());
  revoke = [];
  return {};
};
await app.connect();
