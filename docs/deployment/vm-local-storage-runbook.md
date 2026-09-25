# VM-local storage runbook

This is the storage contract for the first Azure release. It applies to the
production Compose file only and does not change application behavior.

## Boundary and layout

`ORYXENAI_DATA_ROOT` defaults to `/srv/oryxenai`. It must be an absolute path
on the persistent VM disk and must not be the repository checkout. The setup
script creates these directories and bind-mounts them into the services. The
root directory itself is owned by `root:root` with mode `0711`: service users
can traverse to their bind-mounted child, but cannot list the storage root.
Child directories use the service-specific owners and modes below:

| Host path below the data root | Container path | Owner | Purpose |
| --- | --- | --- | --- |
| `postgres` | `/var/lib/postgresql/data` | `postgres` from the pinned image | PostgreSQL database and durable jobs |
| `image-search-cache` | `/app/.workspace/image-search-cache` | `oryxen:oryxen` | Image retrieval cache |
| `caddy/data` | `/data` | non-root `1001:1001` forced by Compose | Certificates and Caddy state |
| `caddy/config` | `/config` | non-root `1001:1001` forced by Compose | Caddy runtime configuration state |

The Dockerfile fixes the application image identity at UID/GID `1001:1001`.
`storage-init` discovers the non-root `postgres` identity from the pinned image
and uses the Compose-enforced `1001:1001` identity for Caddy. The pinned
upstream Caddy image has no named `caddy` account, so Compose sets its user
explicitly and grants only `NET_BIND_SERVICE` for ports 80/443.

The worker and `preview-gateway` share only `preview`. Caches, workspaces,
checkpoints, generated artifacts, exports, and Caddy state are not shared
with the gateway. No service other than Caddy publishes a host port; the
public boundary remains ports 80 and 443.

## Capacity and retention

The example configuration sets a warning threshold of 20 GiB free and a hard
minimum of 10 GiB free on the filesystem containing `ORYXENAI_DATA_ROOT`.
Change `ORYXENAI_STORAGE_WARN_FREE_GIB` and
`ORYXENAI_STORAGE_MIN_FREE_GIB` in the VM-local `.env` when the VM disk size
is different. `doctor` fails below the minimum and warns below the higher
threshold.

The initial operating policy is:

- keep active previews and their metadata until the session is deleted or the
  application’s owner/admin cleanup has completed;
- retain abandoned preview objects for 3 days;
- retain rebuildable image/npm caches for 30 days before manual cleanup.

The retention values are recorded in the VM `.env`; cleanup must be a reviewed
operator action that excludes active pointers and in-flight runs. Do not run a
recursive delete against the data root while diagnosing an incident.

## Setup and checks

On the VM, after creating the fresh `.env` and rendered production overlay:

```bash
./scripts/azure-deploy.sh storage-init
./scripts/azure-deploy.sh doctor
./scripts/azure-deploy.sh disk-check
```

`storage-init` creates the directories with image-derived non-root ownership.
`doctor` validates the environment, production overlay, ownership, disk
thresholds, and merged Compose configuration. `disk-check` is useful from a
cron or operator check without printing environment values.

After the stack is running, the release verification path runs health checks,
Caddy validation, the credential-free log scan, and:

```bash
./scripts/azure-deploy.sh storage-smoke
```

For a restart check, run the smoke command, restart only the worker and
preview gateway, then run it again:

```bash
./scripts/azure-deploy.sh storage-smoke
docker compose -f compose.production.yaml restart worker preview-gateway
./scripts/azure-deploy.sh storage-smoke
```

For the VM reboot gate, run the same sequence after `sudo reboot`; then run
`status`, `doctor`, `storage-smoke`, and the internal health checks. A Docker
restart is not evidence of a VM reboot, so record both results separately.

## Backups

`ORYXENAI_BACKUP_DIR` defaults to `/srv/oryxenai-backups`, outside the live
data root. The backup directory is mode `0700`; backup files are mode `0600`.
Important backups must be copied to owner-controlled storage outside the VM.
A backup kept only on the VM does not protect against VM or disk loss.

Run before a release that changes migrations and after a known-good release:

```bash
./scripts/azure-deploy.sh backup
```

This creates:

- a gzip-compressed plain PostgreSQL dump plus a SHA-256 sidecar; and
- a gzip-compressed archive of the VM-local service state, preview, workspace,
  checkpoint, cache, artifact, export, and Caddy directories, excluding the
  live PostgreSQL data directory (the SQL dump is the database backup).

The backup command never calls `docker compose down -v`.

## Restore dry run and recovery

Validate a backup without touching the live stack:

```bash
./scripts/azure-deploy.sh restore-dry-run /srv/oryxenai-backups/<file>.sql.gz
./scripts/azure-deploy.sh restore-dry-run /srv/oryxenai-backups/<file>.tar.gz
```

The command checks gzip/tar readability and the optional SHA-256 sidecar. It
does not extract files or modify PostgreSQL.

For an actual recovery, first freeze generation traffic and preserve the
current data root. Restore the filesystem archive into a newly initialized
data root, run `storage-init`, start a clean PostgreSQL directory, and restore
the SQL dump through `psql` before starting the application services. Validate
migrations, health, artifact read-back, preview read-back, and Caddy routing
before reopening traffic. Perform the SQL restore in a disposable PostgreSQL
instance first when the incident allows; a raw live-directory replacement is
not a safe database restore.

Use `docker compose stop` or service-specific `docker compose restart` during
maintenance. Never use `docker compose down -v`: the `-v` flag destroys the
persistent database and service volumes.

## Current storage blocker

**Confirmed inert for the first Azure deployment (2026-09-21):** the only two
call sites for `create_artifact_store()` are `AdminService._cleanup_artifacts`
(`src/oryxenai/auth/admin/service.py`), which only constructs the store when
it actually finds an `ArtifactReference`-shaped value while scanning a
