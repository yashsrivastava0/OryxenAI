# Public Google registration and browser-session boundary

## What changed

OryxenAI now has two explicit application admission modes in
`config/app.toml` / `config/app.docker.toml`:

- `open`: after Supabase verifies the Google identity and email, any account
  may be provisioned as a normal user until the database-owned limit of 15 is
  reached. The two bootstrap administrators remain server-configured and do
  not consume those slots.
- `allowlist`: only normalized emails in
  `ORYXENAI_ALLOWED_USER_EMAILS` may be provisioned. This is the restricted
  development or private-environment option.

The application never trusts a browser flag for this choice. The server reads
the committed mode, verifies the Supabase JWT and provider identity, checks
deleted/suspended state, and performs the capacity transaction before creating
an `app_users` row.

## Why a new Google account can still fail

Application admission is not the same as Google's OAuth audience. The current
Google Auth Platform project is in **Testing**, so Google only completes OAuth
for its configured test users. To accept arbitrary accounts on a deployment:

1. Publish the Google OAuth consent configuration for the deployed project (or
   keep adding test users while it is in Testing).
2. Add the deployed HTTPS origin as an authorized JavaScript origin in Google.
3. Add the deployed `/auth/callback` URL to Supabase's allowed redirect URLs.
4. Keep the Supabase provider callback (`/auth/v1/callback`) in Google's
   authorized redirect URI list.
5. Keep the application `primary_origin` and `allowed_origins` exact; no
   wildcard or localhost origin is accepted in production.

No code or email allowlist update is needed for each new user when `open` is
selected. Capacity exhaustion returns the existing safe access screen and
creates no local user or portfolio state.

## Browser token handling

This is a Jinja/vanilla-JavaScript application whose protected API calls use a
Supabase access token in the browser. That is normal for a browser OAuth client;
the publishable key is also intentionally browser-safe. The implementation
does not render access or refresh tokens into HTML, URL query strings, logs,
errors, or API responses. PKCE callback parameters are removed with
`history.replaceState` before the session is used.

The browser client is pinned and self-hosted, uses PKCE, refreshes sessions
automatically, and persists the managed Supabase session for the longer-lived
login behavior requested by the product. Server authorization still verifies
the token on every protected request and owns roles, ownership, capacity,
entitlements, and admin actions. A malicious script running in the same origin
would still be able to act as the browser user; preventing that requires a
larger HttpOnly-cookie/SSR conversion and is intentionally outside this
simple frontend architecture.

The auth and product shells use `no-store`, a restrictive CSP, `frame-ancestors
'none'`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, and a minimal
Permissions Policy. These controls reduce accidental token exposure without
changing the user flow.
