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

  it("approves content and starts the portfolio build from one explicit click, in that order", async () => {
    const api = await readSource("src/data/api-client.ts");
    expect(api).toContain("/code-generator");
    expect(api).toContain("/preview-grant");
    const app = await readSource("src/app/AppShell.tsx");
    expect(app).toContain('approveLabel="Approve & generate my portfolio"');
    expect(app).toContain("onApproveAndContinue={handleApproveAndGenerate}");
    const flow = app.slice(
      app.indexOf("const handleApproveAndGenerate"),
      app.indexOf("const handleStopStudio"),
    );
    expect(flow.indexOf('runContentMutation("approve")')).toBeGreaterThan(-1);
    expect(flow.indexOf('runContentMutation("approve")')).toBeLessThan(flow.indexOf("startStudio()"));
    // A safety repair of the content plan must never start a build.
    expect(flow).toContain('completed !== "approve"');
  });

  it("embeds the generated page in a theme-specific opaque-origin sandbox", async () => {
    const preview = await readSource("src/components/studio/PreviewPane.tsx");
    expect(preview).toContain('frame.allowsScripts ? "allow-scripts allow-popups allow-popups-to-escape-sandbox" : "allow-popups allow-popups-to-escape-sandbox"');
    expect(preview).not.toContain("allow-same-origin");
    expect(preview).toContain("grant.allows_scripts === true");
    expect(preview).toContain('referrerPolicy="no-referrer"');
  });

  it("repairs a stale incomplete Content result instead of looping on approval", async () => {
    const source = await readSource("src/app/AppShell.tsx");
    expect(source).toContain('error.code !== "CONTENT_ARCHITECT_PUBLIC_SCOPE_INCOMPLETE"');
    expect(source).toContain("Content safety revision started");
    expect(source).toContain("Safely rewrite or omit pending or blocked exact details");
  });
});
