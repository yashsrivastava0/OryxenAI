import {
  Client,
  StreamableHTTPClientTransport,
} from "@modelcontextprotocol/client";
import { createHash } from "node:crypto";
import { appendFile, lstat, mkdir, open, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { pathToFileURL } from "node:url";

const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
const delay = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));
export function validPath(value) {
  if (
    typeof value !== "string" ||
    !value ||
    value.length > 240 ||
    /[\\:\x00-\x1f]/.test(value) ||
    value
      .split("/")
      .some(
        (part) =>
          !part ||
          part.startsWith(".") ||
          /[. ]$/.test(part) ||
          /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part),
      )
  )
    throw new Error("Manifest contains an unsafe path.");
  return value;
}
export async function importProject({
  client,
  link,
  destination,
  resume = false,
}) {
  const transferStarted = performance.now();
  const call = async (name, args) => {
    for (let attempt = 0; attempt < 3; attempt++) {
      let result;
      try {
        result = await client.callTool({ name, arguments: args });
      } catch (error) {
        if (attempt === 2)
          throw new Error(
            "MCP transport unavailable. Resume this import when the connection returns.",
            { cause: error },
          );
        await delay(500 * 2 ** attempt);
        continue;
      }
      const data =
        result.structuredContent ??
        JSON.parse(
          result.content.find((item) => item.type === "text")?.text ?? "{}",
        );
      if (!result.isError && !data.error) return data;
      if (!data.error?.retryable || attempt === 2)
        throw new Error(
          `${data.error?.code ?? "MCP_ERROR"}: ${data.error?.message ?? "The handoff is unavailable."}`,
        );
      await delay(500 * 2 ** attempt);
    }
    throw new Error("MCP transport unavailable.");
  };
  const manifest = await call("get_react_project", { share_link: link });
  if (
    manifest.schema !== "ReactProjectManifest/v1" ||
    !Array.isArray(manifest.files) ||
    manifest.files.length > 256 ||
    !manifest.handoff_id ||
    !Number.isFinite(Date.parse(manifest.expires_at)) ||
    Date.parse(manifest.expires_at) <= Date.now()
  )
    throw new Error("Invalid or expired project manifest.");
  let total = 0;
  const seen = new Set();
  for (const file of manifest.files) {
    validPath(file.path);
    const lower = file.path.toLowerCase();
    if (
      seen.has(lower) ||
      !Number.isSafeInteger(file.bytes) ||
      file.bytes < 0 ||
      !/^[a-f0-9]{64}$/.test(file.sha256)
    )
      throw new Error("Invalid manifest file metadata.");
    seen.add(lower);
    total += file.bytes;
  }
  if (total > 10485760)
    throw new Error("Project exceeds the import size limit.");
  const root = path.resolve(destination);
  const markerPath = path.join(root, ".oryxen-import.json");
  const identity = {
    handoff_id: manifest.handoff_id,
    manifest_sha256: hash(JSON.stringify(manifest.files)),
  };
  try {
    await mkdir(root);
    await writeFile(markerPath, JSON.stringify(identity), { flag: "wx" });
  } catch (error) {
    if (error.code !== "EEXIST" || !resume)
      throw new Error(
        "Choose a new project directory; existing work is never overwritten.",
      );
    if (
      !(await lstat(root)).isDirectory() ||
      (await lstat(root)).isSymbolicLink()
    )
      throw new Error("Import destination must be a real directory.");
    if (
      !(await lstat(markerPath)).isFile() ||
      (await lstat(markerPath)).isSymbolicLink()
    )
      throw new Error("Import marker must be a real file.");
    const marker = JSON.parse(await readFile(markerPath, "utf8"));
    if (
      marker.handoff_id !== identity.handoff_id ||
      marker.manifest_sha256 !== identity.manifest_sha256
    )
      throw new Error("This directory belongs to a different import.");
  }
  const chunks = path.join(root, ".oryxen-chunks");
  await mkdir(chunks, { recursive: true });
  if ((await lstat(chunks)).isSymbolicLink())
    throw new Error("Import staging directory cannot be a symbolic link.");
  for (const file of manifest.files) {
    const pieces = file.path.split("/");
    let directory = root;
    for (const piece of pieces.slice(0, -1)) {
      directory = path.join(directory, piece);
      await mkdir(directory, { recursive: true });
      const info = await lstat(directory);
      if (!info.isDirectory() || info.isSymbolicLink())
        throw new Error("Import path contains a symbolic link.");
    }
    const target = path.join(root, ...pieces);
    try {
      const info = await lstat(target);
      if (
        !info.isFile() ||
        info.isSymbolicLink() ||
        hash(await readFile(target)) !== file.sha256
      )
        throw new Error(
          "An existing file differs from the handoff. It was preserved.",
        );
      continue;
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
    }
    const staging = path.join(chunks, hash(file.path));
    let bytes;
    try {
      if ((await lstat(staging)).isSymbolicLink())
        throw new Error("Import staging file cannot be a symbolic link.");
      bytes = await readFile(staging);
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
      bytes = Buffer.alloc(0);
    }
    if (bytes.length > file.bytes) throw new Error("Invalid resume cursor.");
    while (bytes.length < file.bytes) {
      const chunk = await call("read_react_project_file", {
        share_link: link,
        path: file.path,
        cursor: bytes.length,
      });
      const part = Buffer.from(chunk.data ?? "", "base64");
      const next = bytes.length + part.length;
      if (
        chunk.path !== file.path ||
        chunk.offset !== bytes.length ||
        chunk.encoding !== "base64" ||
        !part.length ||
        part.length > 32768 ||
        next > file.bytes ||
        hash(part) !== chunk.chunk_sha256 ||
        chunk.sha256 !== file.sha256 ||
        chunk.next_cursor !== (next < file.bytes ? next : null)
      )
        throw new Error("Chunk integrity verification failed.");
      bytes = Buffer.concat([bytes, part]);
      await appendFile(staging, part);
    }
    if (hash(bytes) !== file.sha256)
      throw new Error(
        "File integrity verification failed. Remove the helper's damaged staging file before resuming.",
      );
    const handle = await open(target, "wx");
    try {
      await handle.writeFile(bytes);
    } finally {
      await handle.close();
    }
  }
  return {
    directory: root,
    files: manifest.files.length,
    bytes: total,
    handoff_id: manifest.handoff_id,
    timings: {
      transfer_seconds: Number(
        ((performance.now() - transferStarted) / 1000).toFixed(3),
      ),
    },
  };
}

async function main() {
  const args = process.argv.slice(2);
  const option = (key) => args[args.indexOf(key) + 1];
  const endpoint = args.includes("--endpoint") ? option("--endpoint") : null;
  const link =
    process.env.ORYXENAI_SHARE_LINK ||
    (args.includes("--link") ? option("--link") : null);
  const destination = args.includes("--destination")
    ? option("--destination")
    : null;
  if (!endpoint || !link || !destination)
    throw new Error(
      "Specify --endpoint, --destination, and ORYXENAI_SHARE_LINK (or --link).",
    );
  const url = new URL(endpoint);
  if (
    url.protocol !== "https:" &&
    !(
      url.protocol === "http:" &&
      ["127.0.0.1", "localhost"].includes(url.hostname)
    )
  )
    throw new Error("MCP requires HTTPS except on localhost.");
  const client = new Client({
    name: "oryxenai-react-importer",
    version: "1.0.0",
  });
  try {
    await client.connect(new StreamableHTTPClientTransport(url));
    const result = await importProject({
      client,
      link,
      destination,
      resume: args.includes("--resume"),
    });
    if (args.includes("--build")) {
      const buildStarted = performance.now();
      const npm = process.platform === "win32" ? "npm.cmd" : "npm";
      for (const command of [
        ["ci", "--no-audit", "--no-fund"],
        ["run", "typecheck"],
        ["run", "build"],
      ]) {
        execFileSync(npm, command, {
          cwd: result.directory,
          stdio: "inherit",
          shell: process.platform === "win32",
        });
      }
      result.build = "passed";
      result.timings.install_typecheck_build_seconds = Number(
        ((performance.now() - buildStarted) / 1000).toFixed(3),
      );
    }
    console.log(JSON.stringify(result));
  } finally {
    await client.close();
  }
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href)
  main().catch((error) => {
    const detail =
      error instanceof Error
        ? error.message.replace(
            /(?:https?:\/\/[^\s]*\/share\/)?[a-f0-9]{32}\.\d+\.[A-Za-z0-9_-]+/g,
            "[share link]",
          )
        : "The connection failed.";
    console.error(
      `React import failed: ${detail} Existing files were preserved. Resume the helper-owned directory when the handoff is available.`,
    );
    process.exitCode = 1;
  });
