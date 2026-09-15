# Owner checklist

This list separates actions that require the owner's browser, account, or
secret from work that can be performed through the repository and VM.

Do not paste secrets, private SSH keys, `.env` contents, OAuth client secrets,
JWTs, or R2 secret keys into chat or these documents.

## Required before the first server deployment

- [ ] Confirm access to the existing Azure subscription and resource group.
- [ ] Confirm access to the VM SSH private key. Keep it outside the repository.
- [ ] Confirm the private GitHub repository URL and access method. If using a
      VM deploy key, add a repository-scoped read-only key.
- [ ] Confirm the two bootstrap administrator email addresses.
- [ ] Confirm the intended normal-user allowlist. Keep it limited to the
      two- or three-person trial; administrators and normal users must not
      overlap.
- [ ] Confirm the Supabase project and its Google provider configuration.
- [ ] Confirm the Cloudflare R2 bucket, account ID, and a bucket-scoped
      Object Read & Write credential.
- [ ] Confirm every active model-provider credential requested by the current
      `config/models.toml`. The deployment script discovers these names; do
      not rely on model names written in documentation.
- [ ] Decide whether at least one image-provider key should be supplied. It is
      optional for startup but recommended for image-backed portfolio output.
- [ ] Inspect the local `.env` privately. If the malformed token-like line is
      a real credential, revoke or rotate it before production use.

## Values entered during `setup`

The VM-local setup creates a fresh `.env` from `.env.example` and renders the
ignored production overlay. Enter these values at the prompts:

| Prompt | Value/policy |
| --- | --- |
| Application hostname | `app.deploy.me` for the future public hostname |
| Preview hostname | `preview.deploy.me` for the future public hostname |
| R2 account/bucket | The Cloudflare R2 account and private bucket chosen for OryxenAI |
| R2 access/secret | A bucket-scoped Object Read & Write credential; never reuse a broad account token |
| Supabase URL/keys | The existing project coordinates, entered privately |
| Bootstrap administrators | Exactly the two owner-selected admin emails required by production validation |
| Normal-user allowlist | Only the intended trial accounts |
| PostgreSQL password | Let the script generate it; do not invent or reuse the local password |
| Model-provider keys | Required active keys first; optional configured keys only when needed |

The domain does not need DNS records yet. The hostnames are entered now so the
production configuration is ready for Phase B.

## Domain activation after deployment

- [ ] Obtain/control `deploy.me` through the current GitHub Student Developer
      Pack offer or another registrar path.
- [ ] Add an A record for `app.deploy.me` pointing to the VM's current static
      public IP.
- [ ] Add an A record for `preview.deploy.me` pointing to the same IP.
- [ ] In Supabase URL Configuration, set the Site URL to
      `https://app.deploy.me`.
- [ ] Add the exact application redirect URL
      `https://app.deploy.me/auth/callback`.
- [ ] In the Google OAuth client, add `https://app.deploy.me` as the web
      origin and use the exact Supabase callback URL shown in the Supabase
      Google provider page.
- [ ] Wait for DNS propagation and Caddy certificate issuance.
- [ ] Run the external verification command and complete browser acceptance.

## What the owner must do versus what AI can do

The owner must approve Azure account/billing actions, claim the domain, enter
secrets, configure Google/Supabase/R2 dashboards, and perform the final
real-browser login and two-user acceptance. AI can prepare the repository,
run checks, execute the guided VM commands when access is available, inspect
redacted logs, and explain failures.
