# Selected sign-in design: local review

The public access page now puts sign-in and three fictional portfolio previews in the first desktop screen. The deployed application has not changed. No remote branches were pushed.

## Try it locally

A local API preview is running at http://localhost:8001/sign-in. The existing server on port 8000 was left alone.

To restart this preview in PowerShell from the repository:

```powershell
$env:OryxenAI_CONFIG_OVERLAY = "config/app.native.toml"
$env:ORYXENAI_AUTH_PRIMARY_ORIGIN = "http://localhost:8001"
uv run uvicorn oryxenai.main:app --host 127.0.0.1 --port 8001
```

Google OAuth must have the matching localhost callback allowed in the existing provider configuration to complete a real sign-in on this port. Automated verification uses mocked providers. Do not change deployed provider settings just to test the layout. The ordinary local port 8000 remains another option after restarting its server with these changes.

## Review journey

1. Open sign-in: Daybreak is visible immediately, independently of authentication restoration. Google is disabled only while initialization is pending.
2. Choose Nightshift or Velvet: the image and exploration destination update, without downloading portfolio HTML, scripts, or fonts.
3. Explore: one sandboxed iframe opens in a native dialog. A matching image remains during loading. A validated readiness message reveals the portfolio. Loading feedback appears after one second; failure after ten seconds offers Retry and Close.
4. Test Work, About, Contact and project details within each fictional portfolio. Original renderer sections and theme scripts remain in the demo copies.
5. Escape or Close unloads the frame and restores focus and background scrolling. Back closes the dialog and Forward reopens it. Direct links, such as `/sign-in?sample=velvet`, open after anonymous authentication resolution; closing removes only the sample parameter.
6. Google retains existing callback, admission, account, admin, onboarding, and saved workspace destination resolution. Username input has local format feedback; availability and reserved names remain server decisions. Failure retains the entered handle.

## Assets and isolation

`config/showcase.toml` names the demo variants and display delays. `src/oryxenai/auth/showcase/content.json` is a committed copy of the fictional designer fixture. Runtime code never imports tests. Production theme packages and palette catalog were not modified.

Portraits were generated once as fictional professional portraits: Maya Kapoor, Arjun Rao and Elena Vale, in neutral studio backgrounds, natural expressions and simple clothing. Their local WebP images are 640 by 800. No sample browsing invokes an image or text model.

Rebuild the HTML and manifest with the existing development environment:

```powershell
uv run python scripts/prepare_showcase.py
uv run python scripts/prepare_showcase.py --capture
```

The optional `--seed-fixture` replaces demo content from the test fixture deliberately, only during preparation. `--capture` renders each finished demo in Chromium and creates WebP posters and thumbnails; it never uses a crop of the generated sign-in mockup. Restart the API after rebuilding assets, since its manifest is cached for the process lifetime. The committed manifest allowlists assets and pins hashes; Git attributes preserve the exact bundle bytes across Windows and Linux checkouts. The separate public serving route shares private-preview response policy but does not access owner sessions, create database rows, or start stages.

## Verification evidence

Local screenshots and measurements are in `.workspace/sign-in-review/`. Desktop layouts fit at 1280x720, 1366x768, 1440x900 and 1920x1080. Phone widths 320 and 390, intermediate widths 768 and 1024, and a 640x360 effective viewport permit scrolling without horizontal overflow. All three samples loaded under the real iframe response policy. Work/About navigation and Escape inside all three frames were exercised in real Chromium; broader human readability feedback remains part of operator review.

The before/after comparison uses the same machine, anonymous provider mock, Chromium, 1280x720 viewport, reduced motion, and in-memory static assets for both revisions. This isolates client layout behavior from hosting cold starts. Single-run observations:

| Measurement | Before | After |
| --- | --- | --- |
| Page height | 1,804 px | 720 px |
| DOM ready | approximately 647 ms | approximately 361 ms |
| CLS | 0.00495 | 0.00024 |
| Subresource requests | 18 | 22 |
| Transferred subresources | 256,509 bytes | 257,521 bytes |
| Default poster response completed | No equivalent above-fold poster | approximately 74 ms |

Byte measurements in this table exclude the HTML navigation response. Detailed JSON records are in `.workspace/sign-in-review/`. Adding real images leaves subresource bytes approximately unchanged while increasing requests; full portfolios are absent until exploration. Actual localhost-server sample readiness in a separate single run was approximately 0.95 seconds for Daybreak, 0.41 seconds for Nightshift and 1.95 seconds for Velvet. These observations include local machine load and are not production hosting latency measurements or conversion results. No new analytics service was added. Keyboard exploration, Escape within the iframe, focus restoration and Google activation with Enter were checked with mocked providers; human task timing remains part of operator review.

Automated checks cover accessible selection, direct links, Back/Forward, Escape/focus restoration, blocked readiness, timeout/retry, stale messages, iframe cleanup, Google loading/failure, bounded storage restoration, username format, and allowlisted public assets. Existing authentication and Studio regression suites are retained. No live Google account interaction, live model call, production migration, or deployment was performed.

Release remains a separate step after operator testing and explicit instruction, using the exact staging CI-passing commit.


Required local checks passed: Ruff lint, Ruff formatting, mypy, the complete pytest run (including existing Studio regression tests), Node frontend authentication tests, and Alembic upgrade against the native local database. Additional focused browser/API checks cover the finished demo assets and later keyboard/image fallback cases. Optional/live-provider skips remain as reported by pytest. Review logs are in `.workspace/sign-in-review/`.
