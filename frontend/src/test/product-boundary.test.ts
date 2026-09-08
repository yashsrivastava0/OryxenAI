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

  it("contains both the Build Preparation and Code Generator session endpoints (D-081 supersedes D-063's boundary)", async () => {
    // @ts-expect-error vitest runs this contract check in Node
    const fs = await import("node:fs");
    // @ts-expect-error vitest runs this contract check in Node
    const path = await import("node:path");
    const source = fs.readFileSync(path.resolve(process.cwd(), "src/data/api-client.ts"), "utf8");
    expect(source).toContain("/build-preparation");
    expect(source).toContain("/code-generator");
  });

  it("keeps Discovery approval separate from the explicit Content start", async () => {
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
    expect(handler).not.toContain("startContentArchitect");
    expect(handler).toContain("Continue when you are ready to start Content Architect");
    expect(stageSource).toContain('approvalActionLabel="Approve brief"');
    expect(stageSource).toContain("requireApprovalConfirmation={false}");
    expect(stageSource).toContain("onContinueToContent");
    expect(appSource).toContain('state.content.state === "locked"');
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
    expect(source).toContain('state.preparation.state === "locked"');
  });
});
