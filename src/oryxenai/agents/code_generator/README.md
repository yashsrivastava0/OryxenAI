# Code Generator ("Studio")

Stage 3 of the portfolio flow. It turns the approved Content Architect
`page_content` into one verified, previewable page for a fixed, pre-built theme,
and lets the owner change the page's **content** in a chat. Styling, scripts and
extra themes are deliberately out of scope (see "Seams kept" below).

The workflow never chains by itself: the API starts a build only on
`POST /api/v1/sessions/{id}/code-generator/start`. The product UI sends that
request right after the owner's single explicit click, "Approve & generate my
portfolio".

## What a build does

```text
approved page_content
  -> admission (counts and lengths, no model call)
  -> generate_page   one model call -> {"lang", "body_html"}
  -> validate        strict, never auto-fixed (see "Validation")
  -> seal            host-owned <head> + the model's body; sha256-pinned
  -> verify          real browser, best effort (see "Browser verification")
  -> promote         one transaction swaps the live page
```

* One durable job per build, `max_attempts = 1`. There is **no** automatic
  retry, repair call or fallback renderer. A failure stops and is reported
  exactly; the owner decides whether to start again.
* A first build makes one model call. A chat change makes two
  (`interpret_change`, then `generate_page`); a reply-only message makes one;
  a restore makes none.
* The model writes the visible markup only. The host owns the technical
  `<head>` (charset, viewport, title, description, stylesheet link).

## Modules

| Path | Responsibility |
| :--- | :--- |
| `src/oryxenai/themes/` | Immutable, versioned theme packages: byte-pinned stylesheet, local fonts and art, `manifest.json`, an executable markup contract and an HTML subset parser. |
| `schemas.py`, `state.py` | Model envelopes, the failure envelope, and the pure control-plane state machine stored at `current_state['code_generator']`. |
| `admission.py` | Refuses content the template cannot render before any model call. |
| `prompt_builder.py`, `prompts/` | Versioned prompts. The page prompt carries the theme contract and exemplar, never the CSS. |
| `agent.py` | `generate_page` and `interpret_change` through the provider-neutral `ModelClient`. |
| `validate.py` | Strict page validation (see below). |
| `bundle.py` | Composes and seals `index.html`; resolves bundle files. |
| `pipeline.py` | The straight line above; shared by the worker and the CLI. |
| `verify_browser.py` | Headless Chromium verification, answered in process by the production preview router. |
| `changes.py` | The chat edit whitelist, atomic application and the decision a plan makes. |
| `service.py` | Start, stop, state (with reconcile-on-read), chat messages, restore, preview links. |
| `serving.py`, `grants.py` | The grant-addressed preview route and its signed, expiring grants. |
| `diagnostics.py` | Every failure becomes one envelope: what, where, why, what to do. |
| `cli.py`, `dev/` | Developer CLI, deterministic reference renderer and mock model client (never imported by runtime code). |

Worker handler: `src/oryxenai/jobs/handlers/code_generator.py`. Tables:
`portfolio_site_versions`, `portfolio_chat_messages` (migration `0027`, both
`ON DELETE CASCADE` from `portfolio_sessions`).

## Validation

`html.parser` based, strict, no auto-fixing. Errors block publication:

* the body does not parse into the required order or has unclosed elements;
* **closed-world visible text**: every text node and text-bearing attribute must
  be an approved string, a theme-owned chrome string or a host-derived value;
* approved copy appears exactly, once, in its own place (placement table);
* forbidden constructs: scripts, inline styles, `on*` handlers, forms, iframes,
  non-theme URLs, classes outside the theme vocabulary, duplicate ids, links that
  do not resolve, external links without `rel`/`target`.

Cosmetic findings (comments, inert `role`/`data-*`) are warnings in the receipt.

## Failures

Every failure is a `FailureEnvelope`: `code`, `stage`
(`start|interpret|generate|validate|bundle|verify|promote`), `summary`, `cause`,
`where[]` (content field, page element, viewport or request), `expected`/`found`,
`owner`, `retryable`, `action` and a support `reference`. It is stored on the
version row, mirrored in the session state and shown by the Studio. A failed
attempt never replaces the live page. A job that dies without reporting is
reconciled on the next read into `WORKER_LOST`.

## Browser verification

`[code_generator.verification] browser = off | best_effort | required`.

The sealed bundle is opened in headless Chromium at the configured viewports.
Every browser request is answered in process by the production preview router
(same grant check, headers, MIME types and CSP); nothing listens on a port and a
request to another host is blocked and reported. Findings: console/CSP errors,
failed requests, broken images, failed fonts, an unstyled page (errors) and
horizontal overflow (warning). `best_effort` records an unlaunchable browser in
the receipt and still publishes; a defect it finds always blocks. The container
image ships without a browser; build with `--build-arg INSTALL_CHROMIUM=true` to
include one.

## Preview and security

* `GET /preview/g/<grant>/index.html` (and the theme's files) is served
  same-origin, outside `/api`. The grant is a stateless HMAC token over
  `{session, version, expiry}`; mint one with
  `GET /api/v1/sessions/{id}/code-generator/preview-grant`. Optional
  `PREVIEW_GRANT_SECRET` shares grants between API instances; without it each
  process uses a random key and the Studio simply asks for a new link.
* Every preview response carries `Content-Security-Policy: sandbox ...` without
  `allow-same-origin` or `allow-scripts`, `Referrer-Policy: no-referrer`,
  `nosniff` and `noindex`. The Studio embeds it in an iframe sandboxed the same
  way, so generated markup can never reach the app's storage or API.
* Grants are redacted from application and server access logs.

## Chat changes

`POST .../messages` (idempotent `client_message_id`, `base_version_id`, hourly
cap, 1500 characters). `interpret_change` returns typed operations on a
whitelist of content paths; the host applies them to a copy, re-checks the result
with the same admission rules, and builds a new version. Style, layout,
ambiguous and unsupported requests get a reply and build nothing. Removals the
owner marks private restrict older versions that showed the text (they can no
longer be served or restored). `POST .../versions/{id}/restore` copies a verified
version; it never calls a model.

## Developer CLI

```powershell
uv run python -m oryxenai.agents.code_generator.cli prompt   --sample 01_strong_profile
uv run python -m oryxenai.agents.code_generator.cli render   --sample 01_strong_profile --out out/render
uv run python -m oryxenai.agents.code_generator.cli generate --sample 01_strong_profile --out out/mock
uv run python -m oryxenai.agents.code_generator.cli generate --sample 01_strong_profile --live --out out/live
uv run python -m oryxenai.agents.code_generator.cli validate --sample 01_strong_profile --html body.html
```

`generate` runs the production pipeline. `--live` uses the configured model route
and needs the application database for the usage ledger. A failure prints the
same envelope the Studio shows and writes `failure.json`, `trace.json` and the
rejected markup.

## Configuration

`[code_generator]` and `[code_generator.verification]` in `config/app.toml`
(limits, theme id, preview link lifetime, browser policy); model routes under
`code_generator` in `config/models.toml`; `PREVIEW_GRANT_SECRET` in `.env`.

## Seams kept

A single retry loop, a single repair call and a clearly labelled degraded render
can be added in `pipeline.py` without touching the stages around them. New themes
are new packages under `src/oryxenai/themes/`; a bundle already lists its files
by hash, so scripts or extra stylesheets can join the manifest later.
