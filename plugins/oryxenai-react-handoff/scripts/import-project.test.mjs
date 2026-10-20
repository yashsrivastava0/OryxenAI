import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createHash } from "node:crypto";
import { importProject, validPath } from "./import-project.mjs";

const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");

test("corrupt binary chunks never become project files", async () => {
  const sample = fixture();
  const original = sample.client.callTool;
  sample.client.callTool = async (args) => {
    const result = await original(args);
    if (args.name === "read_react_project_file")
      result.structuredContent.data = Buffer.from("corrupt").toString("base64");
    return result;
  };
  const parent = await mkdtemp(path.join(tmpdir(), "oryxen-corrupt-"));
  const destination = path.join(parent, "portfolio");
  await assert.rejects(
    importProject({ client: sample.client, link: "test", destination }),
    /integrity/,
  );
  await assert.rejects(readFile(path.join(destination, "src/main.tsx")), {
    code: "ENOENT",
  });
});
function fixture() {
  const files = new Map([
    [
      "src/main.tsx",
      Buffer.from("export const App = () => <h1>你好 React</h1>;"),
    ],
    [
      "public/font.woff2",
      Buffer.from(Array.from({ length: 90000 }, (_, i) => i % 256)),
    ],
  ]);
  const manifest = {
    schema: "ReactProjectManifest/v1",
    handoff_id: "test",
    expires_at: new Date(Date.now() + 60000).toISOString(),
    files: [...files].map(([name, data]) => ({
      path: name,
      bytes: data.length,
      sha256: hash(data),
    })),
  };
  let requests = 0,
    fail = false;
  const client = {
    async callTool({ name, arguments: args }) {
      if (name === "get_react_project") return { structuredContent: manifest };
      requests++;
      if (fail)
        return {
          isError: true,
          structuredContent: {
            error: { code: "EXPIRED", message: "Expired", retryable: false },
          },
        };
      const bytes = files.get(args.path),
        data = bytes.subarray(args.cursor, args.cursor + 32768);
      return {
        structuredContent: {
          path: args.path,
          offset: args.cursor,
          encoding: "base64",
          data: data.toString("base64"),
          chunk_sha256: hash(data),
          sha256: hash(bytes),
          next_cursor:
            args.cursor + data.length < bytes.length
              ? args.cursor + data.length
              : null,
        },
      };
    },
  };
  return {
    client,
    files,
    manifest,
    requests: () => requests,
    fail: () => {
      fail = true;
    },
  };
}

test("binary files transfer outside context and resume without overwriting", async () => {
  const f = fixture(),
    parent = await mkdtemp(path.join(tmpdir(), "react-import-")),
    destination = path.join(parent, "project");
  await importProject({ client: f.client, link: "test", destination });
  for (const [name, bytes] of f.files)
    assert.deepEqual(await readFile(path.join(destination, name)), bytes);
  const requests = f.requests();
  await importProject({
    client: f.client,
    link: "test",
    destination,
    resume: true,
  });
  assert.equal(f.requests(), requests);
  await assert.rejects(
    importProject({ client: f.client, link: "test", destination }),
    /existing work/,
  );
  await writeFile(path.join(destination, "src/main.tsx"), "user changes");
  await assert.rejects(
    importProject({
      client: f.client,
      link: "test",
      destination,
      resume: true,
    }),
    /preserved/,
  );
  assert.equal(
    await readFile(path.join(destination, "src/main.tsx"), "utf8"),
    "user changes",
  );
});

test("expiry leaves an import resumable", async () => {
  const f = fixture(),
    parent = await mkdtemp(path.join(tmpdir(), "react-import-")),
    destination = path.join(parent, "project");
  f.fail();
  await assert.rejects(
    importProject({ client: f.client, link: "test", destination }),
    /EXPIRED/,
  );
  assert.equal(
    JSON.parse(await readFile(path.join(destination, ".oryxen-import.json")))
      .handoff_id,
    "test",
  );
});

test("unsafe paths and case-colliding manifests fail before creating a directory", async () => {
  for (const name of [
    "../x",
    "/x",
    "a\\b",
    ".env",
    "a//x",
    "C:/x",
    "NUL.txt",
    "a/COM1",
    "a/x.",
  ])
    assert.throws(() => validPath(name));
  const f = fixture();
  f.manifest.files.push({ ...f.manifest.files[0], path: "SRC/main.tsx" });
  const parent = await mkdtemp(path.join(tmpdir(), "react-import-"));
  await assert.rejects(
    importProject({
      client: f.client,
      link: "test",
      destination: path.join(parent, "project"),
    }),
    /metadata/,
  );
});
