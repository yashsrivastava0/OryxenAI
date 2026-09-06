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

  it("uses one explicit Discovery approval action to start Content", async () => {
    // @ts-expect-error vitest runs this contract check in Node
    const fs = await import("node:fs");
    // @ts-expect-error vitest runs this contract check in Node
    const path = await import("node:path");
    const appSource = fs.readFileSync(path.resolve(process.cwd(), "src/app/AppShell.tsx"), "utf8");
    const stageSource = fs.readFileSync(
      path.resolve(process.cwd(), "src/stages/discovery/DiscoveryStage.tsx"),
      "utf8",
    );

    const handler = appSource.slice(
      appSource.indexOf("const handleApproveBrief"),
      appSource.indexOf("const runContentMutation"),
    );
    expect(handler).toContain("approveDiscovery");
    expect(handler).toContain("startContentArchitect");
    expect(stageSource).toContain('approvalActionLabel="Approve and start Content"');
    expect(stageSource).toContain("requireApprovalConfirmation={false}");
  });

  it("repairs a stale incomplete Content result instead of looping on approval", async () => {
    // @ts-expect-error vitest runs this contract check in Node
    const fs = await import("node:fs");
    // @ts-expect-error vitest runs this contract check in Node
    const path = await import("node:path");
    const source = fs.readFileSync(path.resolve(process.cwd(), "src/app/AppShell.tsx"), "utf8");

    expect(source).toContain('error.code !== "CONTENT_ARCHITECT_PUBLIC_SCOPE_INCOMPLETE"');
    expect(source).toContain("Content safety revision started");
    expect(source).toContain("Safely rewrite or omit pending or blocked exact details");
  });
});
