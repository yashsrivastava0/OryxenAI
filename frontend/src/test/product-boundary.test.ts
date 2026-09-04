import { describe, expect, it } from "vitest";

declare const process: { cwd: () => string };

describe("authenticated product boundary", () => {
  it("renders the logout hook expected by the auth bootstrap", async () => {
    // @ts-expect-error vitest runs this contract check in Node
    const fs = await import("node:fs");
    // @ts-expect-error vitest runs this contract check in Node
    const path = await import("node:path");
    const source = fs.readFileSync(path.resolve(process.cwd(), "src/app/AppShell.tsx"), "utf8");
    expect(source).toContain('id="app-logout"');
    expect(source).toContain('id="app-admin-link"');
  });

  it("contains no later-stage endpoint in the product API client", async () => {
    // @ts-expect-error vitest runs this contract check in Node
    const fs = await import("node:fs");
    // @ts-expect-error vitest runs this contract check in Node
    const path = await import("node:path");
    const source = fs.readFileSync(path.resolve(process.cwd(), "src/data/api-client.ts"), "utf8");
    expect(source).not.toContain("/build-preparation");
    expect(source).not.toContain("/code-generator");
  });
});
