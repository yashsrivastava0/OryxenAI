import { describe, expect, it } from "vitest";

declare const process: { cwd: () => string };

async function readSource(relativePath: string): Promise<string> {
  // @ts-expect-error vitest runs this contract check in Node
  const fs = await import("node:fs");
  // @ts-expect-error vitest runs this contract check in Node
  const path = await import("node:path");
  return fs.readFileSync(path.resolve(process.cwd(), relativePath), "utf8");
}

describe("authenticated product boundary", () => {
  it("renders the logout and administration hooks expected by the auth shell", async () => {
    const source = await readSource("src/app/AppShell.tsx");
    expect(source).toContain('id="app-logout"');
    expect(source).toContain('id="app-admin-link"');
  });

  it("uses the Discovery and Content Architect session endpoints", async () => {
    const source = await readSource("src/data/api-client.ts");
    expect(source).toContain("/discovery");
    expect(source).toContain("/content-architect");
  });

  it("commits Discovery approval before offering the Content Architect start", async () => {
    const appSource = await readSource("src/app/AppShell.tsx");
    const stageSource = await readSource("src/stages/discovery/DiscoveryStage.tsx");
    const approveOnlyHandler = appSource.slice(
      appSource.indexOf("const handleApproveBrief ="),
      appSource.indexOf("const runContentMutation"),
    );
    expect(approveOnlyHandler).toContain("approveDiscovery");
    expect(approveOnlyHandler).not.toContain("startContentArchitect");
    expect(appSource).toContain("startContentAfterApproval");
    expect(appSource).toContain("onApproveAndContinue={handleApproveBrief}");
    expect(appSource).toContain("onStartNextStage={startContentAfterApproval}");
    expect(stageSource).toContain("onApproveAndContinue");
    expect(appSource).toContain('const contentState = state.content?.state ?? (discoveryApproved ? "available" : "locked")');
  });

  it("repairs a stale incomplete Content result instead of looping on approval", async () => {
    const source = await readSource("src/app/AppShell.tsx");
    expect(source).toContain('error.code !== "CONTENT_ARCHITECT_PUBLIC_SCOPE_INCOMPLETE"');
    expect(source).toContain("Content safety revision started");
    expect(source).toContain("Safely rewrite or omit pending or blocked exact details");
  });
});
