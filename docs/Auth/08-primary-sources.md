# Authentication primary sources

Last reviewed: 2026-08-23.

Provider APIs, limits, pricing, keys, and dashboard behavior change. Recheck
these official sources before implementation and deployment. No tutorial or AI
output is authoritative.

## Supabase Auth

- [Changelog](https://supabase.com/changelog) - scan breaking changes first.
  At the review date, relevant changes include new publishable/secret key
  handling, asymmetric JWT signing, and changed Data API auto-exposure.
- [Auth overview](https://supabase.com/docs/guides/auth)
- [Google login](https://supabase.com/docs/guides/auth/social-login/auth-google)
  - project, scopes, origins, provider callback, and browser OAuth flow.
- [Social login](https://supabase.com/docs/guides/auth/social-login)
- [Redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls) - Site URL,
  exact callback allowlist, wildcard warnings, and error redirects.
- [JWT guidance](https://supabase.com/docs/guides/auth/jwts) - issuer, claims,
  JWKS, asymmetric/shared-secret verification guidance.
- [JWT signing keys](https://supabase.com/docs/guides/auth/signing-keys) -
  rotation, caches, current/standby/revoked behavior.
- [JWT claims reference](https://supabase.com/docs/guides/auth/jwt-fields)
- [Sessions](https://supabase.com/docs/guides/auth/sessions)
- [Auth security](https://supabase.com/docs/guides/auth/security)
- [General Auth configuration](https://supabase.com/docs/guides/auth/general-configuration)
- [Python Auth reference](https://supabase.com/docs/reference/python/auth-getclaims)
- [Admin user management](https://supabase.com/docs/reference/python/admin-api)
  - recheck exact ban, revoke, update, and delete operations before coding.

## Supabase data and platform

- [Billing](https://supabase.com/docs/guides/platform/billing-on-supabase) - Free
  project, Auth/database/storage allowances.
- [Project pausing](https://supabase.com/docs/guides/platform/free-project-pausing)
  - low-activity pause and restore behavior.
- [Database connections](https://supabase.com/docs/guides/database/connecting-to-postgres)
  - direct and pooler modes.
- [Securing the Data API](https://supabase.com/docs/guides/api/securing-your-api)
  - grants, exposed schemas, RLS, and browser roles.
- [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Product security](https://supabase.com/docs/guides/security/product-security)
- [NPM security](https://supabase.com/docs/guides/security/npm-security)

## Google OAuth

- [Google Identity web setup](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid)
- [OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect)
- [OAuth policies](https://developers.google.com/identity/protocols/oauth2/policies)
  - secure origins, authorized domains, homepage/privacy, and secret handling.
- [OAuth app verification](https://support.google.com/cloud/answer/13463073)
- [When verification is not needed](https://support.google.com/cloud/answer/13464323)
- [Manage OAuth clients](https://support.google.com/cloud/answer/15549257)
- [Brand verification](https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification)
- [Google testing versus production audience](https://support.google.com/cloud/answer/15549945)

## Security and standards

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP OAuth 2.0 Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/OAuth2_Cheat_Sheet.html)
- [OWASP JWT Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [OAuth 2.0 Security Best Current Practice, RFC 9700](https://www.rfc-editor.org/rfc/rfc9700)

## AWS timing and cost

- [AWS Free plan](https://aws.amazon.com/free/) - current credits and duration.
- [AWS free-plan selection](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)
  - no-charge/free-plan boundary, closure, auto-upgrade triggers.
- [AWS India account setup](https://docs.aws.amazon.com/accounts/latest/reference/managing-accounts-india.html)
  - current identity/payment verification behavior.
- [Track Free Tier usage](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/tracking-free-tier-usage.html)

## Repository sources of truth

Reinspect at implementation time:

- `AGENTS.md`, `DECISIONS.md`, and `CHANGES.md`;
- `src/oryxenai/core/settings.py`;
- `src/oryxenai/main.py` and `src/oryxenai/api/dependencies.py`;
- every module in `src/oryxenai/api/routes/`;
- `src/oryxenai/db/models/` and repositories;
- `src/oryxenai/jobs/` and each agent service/handler;
- `src/oryxenai/web/routes.py`, templates, and static JavaScript;
- `src/oryxenai/preview/gateway.py`;
- `migrations/versions/` and `tests/`;
- `docs/code-generator-architecture/free-host-deployment.md`; and
- `docs/code-generator-architecture/live-preview-and-deployment.md`.

## Verified development evidence

The sanitized current setup and check output are recorded in
[09-confirmed-setup.md](09-confirmed-setup.md). Run the reusable checker rather
than trusting the dated record:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-auth-prerequisites.ps1 -Online -RequireNormalUser
```
