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

  it("fuses Discovery brief approval with starting Content Architect in one user action", async () => {
    // @ts-expect-error vitest runs this contract check in Node
    const fs = await import("node:fs");
    // @ts-expect-error vitest runs this contract check in Node
    const path = await import("node:path");
    const appSource = fs.readFileSync(path.resolve(process.cwd(), "src/app/AppShell.tsx"), "utf8");
    const stageSource = fs.readFileSync(
      path.resolve(process.cwd(), "src/stages/discovery/DiscoveryStage.tsx"),
      "utf8",
    );

    // handleApproveBrief itself only approves; the fused handler (used by
    // the single UI action) explicitly composes it with starting Content.
    const approveOnlyHandler = appSource.slice(
      appSource.indexOf("const handleApproveBrief ="),
      appSource.indexOf("const handleApproveBriefAndContinue"),
    );
    expect(approveOnlyHandler).toContain("approveDiscovery");
    expect(approveOnlyHandler).not.toContain("startContentArchitect");

    const fusedHandler = appSource.slice(
      appSource.indexOf("const handleApproveBriefAndContinue"),
      appSource.indexOf("const runContentMutation"),
    );
    expect(fusedHandler).toContain("handleApproveBrief()");
    expect(fusedHandler).toContain('selectStage("content")');
    expect(fusedHandler).toContain("runContentMutation");

    expect(stageSource).toContain("onApproveAndContinue");
    expect(appSource).toContain('state.content.state === "locked"');
    // Every stage now shares one fused action (no more per-stage
    // confirm-then-continue asymmetry) — Content->Design must use the same
    // shape as Discovery->Content and Design->Prepare.
    expect(appSource).toContain("handleApproveContentAndContinue");
    expect(appSource).toContain("handleApproveDesignAndContinue");
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
