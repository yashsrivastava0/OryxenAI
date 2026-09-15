# Deployment research sources

Checked 2026-09-15. Recheck provider pages before execution because prices,
student offers, product limits, and dashboards can change.

## Azure

- [Azure for Students](https://learn.microsoft.com/en-us/azure/education-hub/about-azure-for-students)
  describes the student credit and eligibility period. The guide must not
  hardcode a future balance or renewal assumption.
- [Azure spending limits](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit)
  explains that exhausting included credit can disable services and stop or
  deallocate virtual machines. Keep the limit enabled unless the owner makes
  an explicit billing decision.
- [VM states and billing](https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing)
  distinguishes running, stopped, and deallocated states; disks and some
  networking resources can still incur charges after deallocation.
- [Connect to a Linux VM](https://learn.microsoft.com/en-us/azure/virtual-machines/linux-vm-connect)
  confirms the prerequisites used by this runbook: running VM, public IP,
  SSH key, and a narrowly scoped port-22 rule.

## Docker and HTTPS

- [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
  recommends the official Docker apt repository and warns about firewall
  interactions when publishing container ports.
- [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/)
  documents `service_healthy` and `service_completed_successfully`, matching
  the database and migration dependencies in this repository.
- [`docker compose up --wait`](https://docs.docker.com/reference/cli/docker/compose/up/)
  documents waiting for services to be running or healthy.
- [Caddy automatic HTTPS](https://caddyserver.com/docs/automatic-https)
  confirms that public DNS, ports 80/443, and persistent writable certificate
  storage are required for automatic certificates and renewals.

## Authentication and storage

- [Supabase Google login](https://supabase.com/docs/guides/auth/social-login/auth-google)
  covers Google Cloud consent setup, web origins, and the Supabase provider
  callback.
- [Supabase redirect URLs](https://supabase.com/docs/guides/auth/redirect-urls)
  explains Site URL and exact production redirect allowlists.
- [Cloudflare R2 S3 compatibility](https://developers.cloudflare.com/r2/get-started/s3/)
  confirms the endpoint shape, `auto` region, and S3 SDK integration used by
  the application.
- [R2 API tokens](https://developers.cloudflare.com/r2/api/tokens/)
  recommends bucket-scoped Object Read & Write credentials and notes that the
  secret key cannot be viewed again after creation.
- [R2 object lifecycles](https://developers.cloudflare.com/r2/buckets/object-lifecycles/)
  explains prefix-based expiration and the need for a storage-write
  permission when managing lifecycle rules.
- [R2 pricing](https://developers.cloudflare.com/r2/pricing/)
  is the current place to check storage, operation, retrieval, and egress
  policy rather than copying a stale price into project documentation.

## GitHub and the selected domain path

- [GitHub Student Developer Pack](https://education.github.com/pack) is the
  current offer catalogue. The `.me` domain offer and partner may change, so
  the owner should claim the available offer at the time of activation.
- [Student Developer Pack terms](https://docs.github.com/en/education/about-github-education/github-education-for-students/github-terms-and-conditions-for-the-student-developer-pack)
  notes that partner offers have separate terms and can change.
- [GitHub deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
  explains repository-scoped server access and why a read-only key is the
  appropriate default for a simple pull-based deployment.

## Repository conclusions

The implementation-specific conclusions come from the checked-in
`compose.production.yaml`, `Caddyfile`, `config/app.production.toml`,
`config/models.toml`, `.env.example`, `scripts/azure-deploy.sh`, health routes,
storage adapters, authentication settings, and the existing
`docs/deployment` runbook. The production path is implemented but not proven
until the live VM, domain, provider integrations, and browser acceptance all
pass.
