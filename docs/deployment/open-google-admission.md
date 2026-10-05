# Open Google admission release

## Live service observed on 2026-10-06

- Render service: `oryxenai`, `srv-db1nhe60tbcc73bmfpn0`.
- HTTPS origin: `https://app.oryxenai.me`.
- Config overlay: `config/app.render-free.toml`, selected by
  `OryxenAI_CONFIG_OVERLAY` in the Render environment.
- Release branch: `deployment`; Render deploys after its checks pass.
- Last deployed commit at inspection: `dfadfd919b959869f17d95da49001bdcdbf385d5`.
- The live HTML still advertises `admission-mode = allowlist`.

The release checkout is based on that deployed commit. The original `NEW`
worktree contains unrelated edits and a staged rename and was left intact.

## Prepared application change

Both `config/app.render-free.toml` and `config/app.production.toml` use
`admission_mode = "open"`. The existing admission service assigns verified
first-time identities to the normal-user role unless their email is in the
configured bootstrap admin list. Existing database roles remain authoritative.

The bootstrap admin emails are unchanged. The existing normal-user allowlist
can remain configured: open admission ignores it for email admission. Do not
empty the live allowlist before this release; the old allowlist deployment
requires a non-empty list at startup.

The normal-user limit remains defined by `auth.normal_user_limit` in
`config/app.toml` and the database capacity row. Open admission does not remove
this limit. Administrators do not consume normal-user slots.

A read-only aggregate query at inspection returned `normal_user_limit = 15`,
no occupied normal-user slots, and one active administrator account. Render
has two bootstrap admin emails configured; the second account is admitted as
an administrator when it first signs in. No account row was changed.

Public `/privacy` and `/terms` pages describe the demonstration project and
its existing data flow. They require no sign-in, load no authentication
scripts, and expose no authentication configuration. The sign-in footer links
to both pages.

## Cloud configuration observed and prepared

Supabase project: `oxygen-ai-development`, ref `diiestlnmpaarhhexwhi`.

- Allow new users to sign up: enabled.
- Google sign-in: enabled.
- Site URL: `https://app.oryxenai.me`.
- Production redirect: `https://app.oryxenai.me/auth/callback`.
- Callback copied by observation from the Google provider page:
  `https://diiestlnmpaarhhexwhi.supabase.co/auth/v1/callback`.
- Google client ID matches the configured Cloud client; no secret was changed
  or disclosed. Nonce checks remain enabled.

Google Cloud project: `OryxenAI`, id `oryxenai`.

- Audience: External.
- Google client origin includes `https://app.oryxenai.me`.
- The sole authorized redirect URI matches the Supabase callback above.
- Scopes are the non-sensitive `openid`, email, and profile scopes.
- Branding name saved as `OryxenAI`, with homepage `https://app.oryxenai.me`,
  privacy link `https://app.oryxenai.me/privacy`, and terms link
  `https://app.oryxenai.me/terms`.
- Publish app is now enabled. Publishing status remains Testing pending the
  application's release so the new public links are reachable.

Google may require brand/domain verification after publication. Follow the
status shown in its console; basic sign-in scope configuration does not prove
brand verification is complete. See [Google's branding requirements](https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification).

## Local validation

Using the existing local Python environment with this checkout's `src` on
`PYTHONPATH`:

```powershell
python -m pytest tests/unit/auth tests/api/test_auth_phase1.py tests/api/test_web_routes.py tests/api/test_authorization_route_inventory.py -q
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

Build the checked-in frontend source before the product-shell API tests with
`npm ci` and `npm run build` in `frontend/`. The new public pages were also
reviewed in the browser through a local preview with no database or provider
connection. No schema migration or live model call is needed for this change.

## Release and acceptance still required

1. Obtain the operator's review and explicit authorization before promoting
   the reviewed commit through staging CI to `deployment`.
2. Wait for Render's successful deploy and database readiness. Confirm the
   live HTML advertises open admission and both public pages return HTML.
3. Publish the External Google app and inspect the console's verification
   status. Resolve any specific verification requirement Google reports.
4. Choose an available Google account outside both configured email lists.
   Complete sign-in and username onboarding. Confirm it reaches `/app` as a
   normal user, with admin access denied.
5. Recheck the bootstrap admin accounts and normal-user capacity policy.

The real non-admin Google sign-in acceptance test has not passed yet. Unit
tests of a mocked verified identity are not a substitute for this live test.
