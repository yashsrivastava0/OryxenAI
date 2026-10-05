# Render CI/CD runbook

The GitHub repository is `yashsrivastava0/OryxenAI`. `staging` is the integration
branch; it runs the `quality` GitHub Actions job and has no Render service.
`deployment` is the only branch linked to the `oryxenai` Render web service.
Render's **After CI Checks Pass** setting deploys a new `deployment` commit only
when its GitHub checks pass. There is no Azure deploy job and no required PR
review.

## One-time setup

1. In the repository ruleset `deployment-ci-gate`, remove the **Require a pull
   request before merging** rule. Keep deletion protection, force-push
   protection, and the required `Lint, type-check, test, audit` check from
   GitHub Actions. A passing check on the exact release commit must exist
   before its direct push to `deployment`.
2. In the existing `OryxenAI` Render Hobby workspace, project `Origin AI`,
   create the `oryxenai` service from the root `render.yaml`. Confirm its Git
   branch is `deployment`, region Singapore, Free instance, Docker command
   `python -m oryxenai.deployment.render_web`, health path `/health/ready`,
   and Auto-Deploy **After CI Checks Pass**. Creating the service starts its
   first deployment; do this after the release commit is on `deployment`.
3. Enter the `sync: false` values prompted by the Blueprint directly in
   Render: Supabase Session pooler `DATABASE_URL`, Supabase publishable and
   server keys, two admin emails, permitted user emails, and the configured
   model provider key. The Blueprint generates the persistent preview grant
   secret. Never commit or paste secret values into logs or chat.
4. Add `app.oryxenai.me` as a Render custom domain. In Namecheap BasicDNS,
   replace the old `app` A record with the CNAME target displayed by Render.
   Leave the apex A records and mail settings alone. Verify TLS and OAuth at
   the custom domain before treating the release as live.

## Routine release

1. Push work to `staging`. Confirm `quality` is green for the exact SHA in
   GitHub Actions. A failing or missing check stops the release.
2. From a checkout where `staging` is at that SHA, fast-forward `deployment`
   and push it. The concise command is `git push origin staging:deployment`.
   This must be a fast-forward; fetch and reconcile any changed remote tip
   first. Agents require a user's explicit instruction to make this live push.
3. GitHub runs CI on `deployment` again. Render builds and deploys after checks
   pass, then probes `/health/ready`. Watch the Render deploy event and verify
   `/health/ready` and one authenticated browser flow on the custom domain.

The root `render.yaml` is the source of truth for service settings. Render Free
sleeps after inactivity, so the combined web and worker process also sleeps.
The Free overlay reads PDFs with selectable text but does not run scanned-PDF
OCR: a three-page scan exceeded the 120-second limit in a 512 MiB container
even with five times Render Free's CPU allocation. Scanned documents should be
exported as text-based PDFs, pasted as text, or processed in a larger plan with
OCR deliberately enabled and measured.
The optional readiness monitor described in the acceptance runbook keeps it
awake but consumes the workspace's Free instance hours. Monitor usage before
enabling it continuously.

## Recovery

If CI fails, fix the branch and rerun it; Render keeps the previous successful
deploy. If the new service fails readiness, inspect its deployment logs for
migration, database, auth configuration, or memory errors. Redeploy a prior
passing commit through the same `staging` → `deployment` path; do not force-push
`deployment`. The former Azure runner instructions are archived in
`archive/ci-cd-azure-vm.md` for temporary rollback reference.
