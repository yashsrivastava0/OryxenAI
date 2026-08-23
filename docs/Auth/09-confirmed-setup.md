# Confirmed authentication setup

Recorded: 2026-08-23, Asia/Calcutta.

Purpose: preserve the completed, non-secret provider setup for future coding
agents. This file contains no OAuth secret, Supabase key, password, token, card
detail, or full allowlist/bootstrap-email value.

## Accepted decision

| Item | Confirmed value |
| --- | --- |
| Identity provider | Supabase Auth |
| Sign-in method | Google only |
| Other methods | No Clerk, password, email OTP, phone, or SMS |
| Application authorization | FastAPI + PostgreSQL |
| Registration | Application allowlist |
| Normal-user capacity | 15 |
| Initial administrators | 2, excluded from normal capacity |
| Normal-user portfolio policy | One session, one variant, one promoted success |
| Admin portfolio policy | Unlimited entitlement, provider budget still enforced |
| Existing sessions | Legacy/admin-only quarantine |
| Deployment | Deferred; no AWS/production resources now |

## Google Auth Platform

| Setting | Confirmed value |
| --- | --- |
| Project name | `Oxygen.ai` |
| Organization | No organization |
| Audience | External |
| Publishing status | Testing |
| Support contact | Configured privately |
| Additional contact | Configured privately |
| OAuth client type | Web application |
| OAuth client name | `Oxygen.ai Development` |
| Client ID | Generated and entered privately in Supabase |
| Client Secret | Generated and entered privately in Supabase |
| Downloaded JSON | Not required by OryxenAI and must not enter the repository |

Scopes:

```text
openid
userinfo.email
userinfo.profile
```

Development JavaScript origins:

```text
http://localhost:8000
http://127.0.0.1:8000
```

Authorized provider redirect:

```text
https://diiestlnmpaarhhexwhi.supabase.co/auth/v1/callback
```

Two distinct administrator Google accounts are configured privately and are
present in Google's test-user list. Their exact addresses remain in the
git-ignored environment/dashboard rather than committed documentation.

## Supabase development project

| Setting | Confirmed value |
| --- | --- |
| Project name | `oxygen-ai-development` |
| Project reference | `diiestlnmpaarhhexwhi` |
| Project URL | `https://diiestlnmpaarhhexwhi.supabase.co` |
| Region | South Asia (Mumbai), `ap-south-1` |
| Plan/compute | Free / nano |
| Dashboard status at setup | Healthy |
| Application tables | None manually created; Alembic remains authoritative |
| Google provider | Enabled |
| Client ID/Secret | Configured privately |
| Skip nonce checks | Off |
| Allow users without email | Off |

Site URL:

```text
http://localhost:8000
```

Allowed redirect URLs:

```text
http://localhost:8000/auth/callback
http://127.0.0.1:8000/auth/callback
```

## Local environment evidence

The git-ignored `.env` exists. Redaction-safe inspection confirmed:

| Variable | Declared | Nonempty | Notes |
| --- | --- | --- | --- |
| `SUPABASE_URL` | Yes | Yes | Matches the confirmed project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Yes | Yes | Value not printed |
| `SUPABASE_SECRET_KEY` | Yes | Yes | Server-only value not printed |
| `ORYXENAI_ADMIN_BOOTSTRAP_EMAILS` | Yes | Yes | Two distinct expected entries; values not printed |
| `ORYXENAI_ALLOWED_USER_EMAILS` | Yes | No | Intentional until a normal test account exists |

The application does not read these auth settings yet. Presence proves owner
setup only, not implemented auth.

## Live verification evidence

A network check using only locally loaded configuration reported:

```text
auth_settings_reachable=True
google_provider_enabled=True
jwks_reachable=True
jwks_key_count=1
oauth_start_status=302
oauth_redirects_to_google=True
```

No key, token, OAuth location, client identifier, or account information was
printed. The checks prove:

- the configured Auth API accepts the publishable key;
- Google is enabled in the project;
- a public asymmetric verification key is available; and
- the configured OAuth provider can begin a redirect to Google for the local
  callback.

They do not prove the Google Client Secret completes token exchange. That
requires a real browser login after the app callback exists.

## Pending owner-side verification

One separate normal test identity is still required. Do not use either admin as
the normal-user test.

When available:

1. add it to Google OAuth test users;
2. add it privately to `ORYXENAI_ALLOWED_USER_EMAILS`;
3. restart the app after implementation;
4. test approved new user, username, one portfolio, foreign-ID isolation,
   success freeze, and sign-out; and
5. retain both admins for admin-only tests.

Until then, deterministic tests use fake identities and the two real admin
accounts may validate only the administrator Google flow.

## Deliberately not created

- no AWS account, EC2, S3, or CloudFront;
- no production Supabase project;
- no production Google OAuth client;
- no paid cloud resource;
- no application auth tables;
- no Clerk tenant/configuration; and
- no downloaded Google OAuth JSON in the repository.

## Re-run verification

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-auth-prerequisites.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-auth-prerequisites.ps1 -Online
```

Dashboard-only origin/redirect entries and a completed Google token exchange
must still be verified manually in the visible browser acceptance run.
