#!/usr/bin/env bash
#
# Guided deployment and maintenance for the single-VM Azure Compose install.
# The script is intentionally self-contained: the VM needs Git, Bash, curl,
# and sudo; setup installs Docker Engine and the Compose plugin.

set -Eeuo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
ENV_EXAMPLE="$REPO_ROOT/.env.example"
PRODUCTION_TEMPLATE="$REPO_ROOT/config/app.production.toml"
PRODUCTION_LOCAL="$REPO_ROOT/config/app.production.local.toml"
STATE_DIR="$REPO_ROOT/.workspace/azure-deploy"
STATE_FILE="$STATE_DIR/state.env"
DEFAULT_BRANCH="codex/code-generator-control-room"
DEFAULT_DATA_ROOT="/srv/oryxenai"
DEFAULT_BACKUP_DIR="/srv/oryxenai-backups"
DEFAULT_STORAGE_MIN_FREE_GIB="10"
DEFAULT_STORAGE_WARN_FREE_GIB="20"
APP_UID="1001"
APP_GID="1001"
# compose.production.yaml forces Caddy to this non-root identity because the
# pinned upstream image does not ship a named caddy account.
CADDY_UID="1001"
CADDY_GID="1001"
POSTGRES_IMAGE="postgres:16.4-alpine@sha256:5660c2cbfea50c7a9127d17dc4e48543eedd3d7a41a595a2dfa572471e37e64c"

cd "$REPO_ROOT"

info() {
  printf '[azure] %s\n' "$@"
}

warn() {
  printf '[azure] WARNING: %s\n' "$*" >&2
}

die() {
  printf '[azure] ERROR: %s\n' "$*" >&2
  exit 1
}

on_error() {
  local code=$?
  printf '[azure] ERROR: command failed at line %s (exit %s)\n' "${BASH_LINENO[0]}" "$code" >&2
  printf '[azure] Run ./scripts/azure-deploy.sh logs for service details.\n' >&2
  exit "$code"
}

trap on_error ERR

docker_cmd() {
  if docker info >/dev/null 2>&1; then
    docker "$@"
    return
  fi
  sudo docker "$@"
}

compose() {
  docker_cmd compose \
    --project-directory "$REPO_ROOT" \
    -f "$REPO_ROOT/compose.production.yaml" \
    "$@"
}

env_value() {
  local key="$1"
  awk -v key="$key" '
    index($0, key "=") == 1 {
      value = substr($0, length(key) + 2)
      found = 1
    }
    END {
      if (!found) {
        exit 1
      }
      print value
    }
  ' "$ENV_FILE"
}

configured_value() {
  local key="$1"
  local default="$2"
  local value="${!key:-}"

  if [[ -z "$value" && -f "$ENV_FILE" ]]; then
    value="$(env_value "$key" 2>/dev/null || true)"
  fi
  printf '%s\n' "${value:-$default}"
}

data_root() {
  configured_value ORYXENAI_DATA_ROOT "$DEFAULT_DATA_ROOT"
}

backup_root() {
  configured_value ORYXENAI_BACKUP_DIR "$DEFAULT_BACKUP_DIR"
}

storage_min_free_gib() {
  configured_value ORYXENAI_STORAGE_MIN_FREE_GIB "$DEFAULT_STORAGE_MIN_FREE_GIB"
}

storage_warn_free_gib() {
  configured_value ORYXENAI_STORAGE_WARN_FREE_GIB "$DEFAULT_STORAGE_WARN_FREE_GIB"
}

storage_paths() {
  local root
  root="$(data_root)"
  printf '%s\n' \
    "$root/postgres" \
    "$root/preview" \
    "$root/image-search-cache" \
    "$root/npm-cache" \
    "$root/code-generator-development" \
    "$root/code-generator-materials" \
    "$root/code-generator-generation" \
    "$root/code-generator-checkpoints" \
    "$root/code-generator-workspaces" \
    "$root/code-generator-artifacts" \
    "$root/build-preparation-staging" \
    "$root/code-gen-output" \
    "$root/caddy/data" \
    "$root/caddy/config"
}

run_as_root() {
  if [[ "$(id -u)" == "0" ]]; then
    "$@"
  else
    command -v sudo >/dev/null 2>&1 || die "sudo is required for VM storage ownership."
    sudo "$@"
  fi
}

require_absolute_storage_root() {
  local root="$1"
  [[ "$root" = /* && "$root" != "/" ]] || return 1
  [[ "$root" != "$REPO_ROOT" && "$root" != "$REPO_ROOT/" ]] || return 1
}

require_backup_root() {
  local backup="$1"
  local root="$2"
  require_absolute_storage_root "$backup" || return 1
  [[ "$backup" != "$root" && "$backup" != "$root"/* ]] || return 1
}

image_identity() {
  local image="$1"
  local account="$2"
  local uid gid

  uid="$(docker_cmd run --rm --entrypoint /bin/sh "$image" -c "id -u $account")" || \
    die "Could not determine the non-root UID for $account in $image."
  gid="$(docker_cmd run --rm --entrypoint /bin/sh "$image" -c "id -g $account")" || \
    die "Could not determine the non-root GID for $account in $image."
  [[ "$uid" =~ ^[1-9][0-9]*$ && "$gid" =~ ^[1-9][0-9]*$ ]] || \
    die "$image does not expose a non-root identity for $account."
  printf '%s:%s\n' "$uid" "$gid"
}

storage_identities() {
  local postgres_identity
  postgres_identity="$(image_identity "$POSTGRES_IMAGE" postgres)"
  printf 'app=%s:%s\n' "$APP_UID" "$APP_GID"
  printf 'postgres=%s\n' "$postgres_identity"
  printf 'caddy=%s:%s\n' "$CADDY_UID" "$CADDY_GID"
}

storage_identity_value() {
  local name="$1"
  storage_identities | awk -F= -v name="$name" '$1 == name { print $2; exit }'
}

initialize_storage() {
  local root backup postgres_identity caddy_identity path
  root="$(data_root)"
  backup="$(backup_root)"
  require_absolute_storage_root "$root" || \
    die "ORYXENAI_DATA_ROOT must be an absolute path other than / and outside the repository."
  require_backup_root "$backup" "$root" || \
    die "ORYXENAI_BACKUP_DIR must be an absolute path outside the data root and repository."

  postgres_identity="$(storage_identity_value postgres)"
  caddy_identity="$(storage_identity_value caddy)"

  # The root itself is traversable but not listable by service users; each
  # child directory below carries the service-specific ownership and mode.
  run_as_root install -d -m 0711 -o 0 -g 0 "$root"
  run_as_root install -d -m 0700 -o "$(id -u)" -g "$(id -g)" "$backup"

  while IFS= read -r path; do
    case "$path" in
      "$root/postgres")
        run_as_root install -d -m 0700 -o "${postgres_identity%:*}" -g "${postgres_identity#*:}" "$path"
        ;;
      "$root/caddy"/*)
        run_as_root install -d -m 0750 -o "${caddy_identity%:*}" -g "${caddy_identity#*:}" "$path"
        ;;
      *)
        run_as_root install -d -m 0750 -o "$APP_UID" -g "$APP_GID" "$path"
        ;;
    esac
  done < <(storage_paths)

  info "VM storage initialized at $root with non-root service ownership."
}

storage_ownership_check() {
  local root="$1"
  local postgres_identity caddy_identity path owner expected failures=0
  postgres_identity="$(storage_identity_value postgres)"
  caddy_identity="$(storage_identity_value caddy)"

  while IFS= read -r path; do
    if [[ ! -d "$path" ]]; then
      warn "Missing VM storage directory: $path"
      failures=$((failures + 1))
      continue
    fi
    owner="$(stat -c '%u:%g' "$path" 2>/dev/null || true)"
    case "$path" in
      "$root/postgres") expected="$postgres_identity" ;;
      "$root/caddy"/*) expected="$caddy_identity" ;;
      *) expected="$APP_UID:$APP_GID" ;;
    esac
    if [[ "$owner" != "$expected" ]]; then
      warn "VM storage ownership mismatch for $path (got $owner, expected $expected)."
      failures=$((failures + 1))
    fi
  done < <(storage_paths)
  return "$failures"
}

storage_disk_check() {
  local root="$1" free_kib warn_kib min_kib
  local warn_gib min_gib
  require_absolute_storage_root "$root" || {
    warn "ORYXENAI_DATA_ROOT must be an absolute path outside the repository."
    return 1
  }
  [[ -d "$root" ]] || {
    warn "VM data root does not exist: $root"
    return 1
  }
  warn_gib="$(storage_warn_free_gib)"
  min_gib="$(storage_min_free_gib)"
  [[ "$warn_gib" =~ ^[0-9]+$ && "$min_gib" =~ ^[0-9]+$ ]] || {
    warn "Storage free-space thresholds must be whole GiB values."
    return 1
  }
  (( min_gib > 0 && warn_gib >= min_gib )) || {
    warn "Storage thresholds are invalid: warn=$warn_gib GiB min=$min_gib GiB."
    return 1
  }
  free_kib="$(df -Pk "$root" | awk 'NR==2 { print $4 }')"
  [[ "$free_kib" =~ ^[0-9]+$ ]] || {
    warn "Could not read free space for $root."
    return 1
  }
  warn_kib=$((warn_gib * 1048576))
  min_kib=$((min_gib * 1048576))
  if (( free_kib < min_kib )); then
    warn "Critical: only $((free_kib / 1048576)) GiB is free under $root; minimum is $min_gib GiB."
    return 1
  fi
  if (( free_kib < warn_kib )); then
    warn "Warning: only $((free_kib / 1048576)) GiB is free under $root; warning threshold is $warn_gib GiB."
  else
    info "VM storage has $((free_kib / 1048576)) GiB free (warning $warn_gib GiB, minimum $min_gib GiB)."
  fi
}

set_env_value() {
  local key="$1"
  local value="$2"
  local temporary

  temporary="$(mktemp "$REPO_ROOT/.env.tmp.XXXXXX")"
  awk -v key="$key" -v value="$value" '
    BEGIN { replaced = 0 }
    index($0, key "=") == 1 {
      print key "=" value
      replaced = 1
      next
    }
    { print }
    END {
      if (!replaced) {
        print key "=" value
      }
    }
  ' "$ENV_FILE" >"$temporary"
  mv "$temporary" "$ENV_FILE"
}

state_value() {
  local key="$1"
  [[ -f "$STATE_FILE" ]] || return 1
  awk -F= -v key="$key" '
    $1 == key { value = substr($0, index($0, "=") + 1) }
    END {
      if (value == "") {
        exit 1
      }
      print value
    }
  ' "$STATE_FILE"
}

deployment_branch() {
  local branch
  branch="$(state_value DEPLOY_BRANCH 2>/dev/null || true)"
  printf '%s\n' "${branch:-$DEFAULT_BRANCH}"
}

write_state() {
  local last_good="$1"
  local previous_good="$2"
  local branch="$3"

  mkdir -p "$STATE_DIR"
  cat >"$STATE_FILE" <<EOF
LAST_GOOD_SHA=$last_good
PREVIOUS_GOOD_SHA=$previous_good
DEPLOY_BRANCH=$branch
DEPLOYED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF
  chmod 600 "$STATE_FILE"
}

ask_visible() {
  local label="$1"
  local default="${2:-}"
  local answer

  if [[ -n "$default" ]]; then
    read -r -p "$label [$default]: " answer
    REPLY="${answer:-$default}"
  else
    read -r -p "$label: " REPLY
  fi
}

ask_required() {
  local label="$1"
  while :; do
    ask_visible "$label"
    [[ -n "$REPLY" ]] && return
    warn "This value is required."
  done
}

ask_secret() {
  local label="$1"
  read -r -s -p "$label: " REPLY
  printf '\n'
}

ask_required_secret() {
  local label="$1"
  while :; do
    ask_secret "$label"
    [[ -n "$REPLY" ]] && return
    warn "This value is required."
  done
}

ask_optional_secret() {
  local label="$1"
  read -r -s -p "$label (press Enter to skip): " REPLY
  printf '\n'
}

sed_escape() {
  printf '%s' "$1" | sed 's/[&|]/\\&/g'
}

active_model_keys() {
  local fallback profile key
  local -a profiles=()
  local -a routed_profiles=()

  fallback="$(awk -F'"' '/^[[:space:]]*fallback_profile[[:space:]]*=/ { print $2; exit }' \
    "$REPO_ROOT/config/models.toml")"
  [[ -n "$fallback" ]] && profiles+=("$fallback")

  mapfile -t routed_profiles < <(
    awk -F'"' '
      /^\[routing\.engine_profiles\]$/ { in_section = 1; next }
      in_section && /^\[/ { exit }
      in_section && /^[[:space:]]*[A-Za-z0-9_]+[[:space:]]*=/ { print $2 }
    ' "$REPO_ROOT/config/models.toml"
  )
  profiles+=("${routed_profiles[@]}")

  for profile in "${profiles[@]}"; do
    key="$(awk -F'"' -v section="[profiles.$profile]" '
      $0 == section { in_profile = 1; next }
      in_profile && /^\[/ { exit }
      in_profile && /^[[:space:]]*api_key_env[[:space:]]*=/ { print $2; exit }
    ' "$REPO_ROOT/config/models.toml")"
    [[ -n "$key" ]] && printf '%s\n' "$key"
  done | sort -u
}

render_production_config() {
  [[ -f "$PRODUCTION_TEMPLATE" ]] || die "Missing $PRODUCTION_TEMPLATE"
  [[ -f "$ENV_FILE" ]] || die "Missing $ENV_FILE; run setup first."

  local app_host preview_host temporary
  app_host="$(env_value APP_HOST 2>/dev/null || true)"
  preview_host="$(env_value PREVIEW_HOST 2>/dev/null || true)"

  [[ -n "$app_host" ]] || die "APP_HOST is missing from .env"
  [[ -n "$preview_host" ]] || die "PREVIEW_HOST is missing from .env"

  temporary="$(mktemp "$REPO_ROOT/config/app.production.local.toml.XXXXXX")"
  sed \
    -e "s|<APP_HOST>|$(sed_escape "$app_host")|g" \
    -e "s|<PREVIEW_HOST>|$(sed_escape "$preview_host")|g" \
    "$PRODUCTION_TEMPLATE" >"$temporary"
  mv "$temporary" "$PRODUCTION_LOCAL"
  chmod 644 "$PRODUCTION_LOCAL"
}

install_docker() {
  if command -v docker >/dev/null 2>&1 \
    && docker_cmd compose version >/dev/null 2>&1 \
    && docker_cmd info >/dev/null 2>&1; then
    info "Docker Engine and Compose are already available."
    return
  fi

  command -v sudo >/dev/null 2>&1 || die "sudo is required to install Docker."
  info "Installing Docker Engine from the official Ubuntu repository."
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc

  # shellcheck disable=SC1091
  . /etc/os-release
  local codename="${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}"
  [[ -n "$codename" ]] || die "Could not determine the Ubuntu codename."
  local architecture
  architecture="$(dpkg --print-architecture)"

  sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $codename
Components: stable
Architectures: $architecture
Signed-By: /etc/apt/keyrings/docker.asc
EOF

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER" || true
  info "Docker is installed. The script will use sudo until a new SSH session picks up the docker group."
}

write_initial_env() {
  [[ -f "$ENV_EXAMPLE" ]] || die "Missing $ENV_EXAMPLE"
  [[ ! -e "$ENV_FILE" ]] || die "$ENV_FILE already exists; use configure instead."

  umask 077
  cp "$ENV_EXAMPLE" "$ENV_FILE"

  ask_required "Application hostname, for example app.example.com"
  set_env_value APP_HOST "$REPLY"
  ask_required "Preview hostname, for example preview.example.com"
  set_env_value PREVIEW_HOST "$REPLY"
  ask_visible "Persistent VM data root" "$DEFAULT_DATA_ROOT"
  set_env_value ORYXENAI_DATA_ROOT "$REPLY"
  ask_visible "Backup directory (outside the live data root)" "$DEFAULT_BACKUP_DIR"
  set_env_value ORYXENAI_BACKUP_DIR "$REPLY"

  ask_required_secret "Supabase URL"
  set_env_value SUPABASE_URL "$REPLY"
  ask_required_secret "Supabase publishable key"
  set_env_value SUPABASE_PUBLISHABLE_KEY "$REPLY"
  ask_required_secret "Supabase secret key"
  set_env_value SUPABASE_SECRET_KEY "$REPLY"
  ask_required "Two bootstrap administrator emails, comma-separated"
  set_env_value ORYXENAI_ADMIN_BOOTSTRAP_EMAILS "$REPLY"
  ask_required "Allowed normal-user emails, comma-separated"
  set_env_value ORYXENAI_ALLOWED_USER_EMAILS "$REPLY"

  if command -v openssl >/dev/null 2>&1; then
    set_env_value POSTGRES_PASSWORD "$(openssl rand -hex 24)"
    info "Generated a PostgreSQL password and stored it only in .env."
  else
    ask_secret "PostgreSQL password"
    set_env_value POSTGRES_PASSWORD "$REPLY"
  fi

  mapfile -t model_keys < <(
    awk -F'"' '/^[[:space:]]*api_key_env[[:space:]]*=/ && $2 != "" { print $2 }' \
      "$REPO_ROOT/config/models.toml" | sort -u
  )
  mapfile -t active_keys < <(active_model_keys)
  declare -A required_model_keys=()
  for key in "${active_keys[@]}"; do
    required_model_keys["$key"]=1
  done
  for key in "${model_keys[@]}"; do
    if [[ "${required_model_keys[$key]:-0}" == 1 ]]; then
      ask_required_secret "Required active model/provider key $key"
    else
      ask_optional_secret "Optional model/provider key $key"
    fi
    if [[ -n "$REPLY" ]]; then
      set_env_value "$key" "$REPLY"
    fi
  done

  chmod 600 "$ENV_FILE"
  render_production_config
}

doctor() {
  local failures=0
  local key value host root backup
  local docker_ready=0
  local -a active_keys=()

  info "Checking deployment prerequisites."
  if ! command -v docker >/dev/null 2>&1; then
    warn "Docker is not installed."
    failures=$((failures + 1))
  elif ! docker_cmd compose version >/dev/null 2>&1; then
    warn "Docker Compose plugin is not available."
    failures=$((failures + 1))
  elif ! docker_cmd info >/dev/null 2>&1; then
    warn "The Docker daemon is not reachable."
    failures=$((failures + 1))
  else
    info "Docker and Compose are available."
    docker_ready=1
  fi

  [[ -f "$ENV_FILE" ]] || {
    warn "Missing .env."
    failures=$((failures + 1))
  }
  [[ -f "$PRODUCTION_LOCAL" ]] || {
    warn "Missing config/app.production.local.toml; run setup or configure."
    failures=$((failures + 1))
  }

  if [[ -f "$ENV_FILE" ]]; then
    for key in \
      POSTGRES_PASSWORD \
      APP_HOST \
      PREVIEW_HOST \
      ORYXENAI_DATA_ROOT \
      ORYXENAI_BACKUP_DIR \
      SUPABASE_URL \
      SUPABASE_PUBLISHABLE_KEY \
      SUPABASE_SECRET_KEY \
      ORYXENAI_ADMIN_BOOTSTRAP_EMAILS \
      ORYXENAI_ALLOWED_USER_EMAILS; do
      value="$(env_value "$key" 2>/dev/null || true)"
      if [[ -z "$value" || "$value" == *"<"* || "$value" == *">"* \
        || "$value" == "app.example.com" || "$value" == "preview.example.com" ]]; then
        warn "$key is missing or still contains a placeholder."
        failures=$((failures + 1))
      fi
    done

    mapfile -t active_keys < <(active_model_keys)
    for key in "${active_keys[@]}"; do
      value="$(env_value "$key" 2>/dev/null || true)"
      if [[ -z "$value" || "$value" == *"<"* || "$value" == *">"* ]]; then
        warn "$key is required by the active model routing but is missing."
        failures=$((failures + 1))
      fi
    done

    value="$(env_value POSTGRES_PASSWORD 2>/dev/null || true)"
    if [[ "$value" == "oryxenlocal" ]]; then
      warn "POSTGRES_PASSWORD is still the known .env.example default; set a real password."
      failures=$((failures + 1))
    fi

    if command -v stat >/dev/null 2>&1; then
      local mode
      mode="$(stat -c '%a' "$ENV_FILE" 2>/dev/null || true)"
      [[ "$mode" == "600" ]] || warn ".env permissions are $mode; expected 600."
    fi

    for host in "$(env_value APP_HOST 2>/dev/null || true)" "$(env_value PREVIEW_HOST 2>/dev/null || true)"; do
      [[ -n "$host" ]] || continue
      if command -v getent >/dev/null 2>&1 && ! getent hosts "$host" >/dev/null 2>&1; then
        warn "$host does not resolve yet; DNS must resolve before HTTPS verification."
      fi
    done
  fi

  if [[ -f "$PRODUCTION_LOCAL" ]] && grep -Eq '<(APP_HOST|PREVIEW_HOST)>' "$PRODUCTION_LOCAL"; then
    warn "Production configuration still contains placeholders."
    failures=$((failures + 1))
  fi

  if [[ -f "$PRODUCTION_LOCAL" ]] && grep -Eiq 'R2|S3|cloudflare' "$PRODUCTION_LOCAL"; then
    warn "Production configuration still contains a retired cloud-storage requirement."
    failures=$((failures + 1))
  fi

  root="$(data_root)"
  backup="$(backup_root)"
  if ! require_absolute_storage_root "$root" 2>/dev/null; then
    warn "ORYXENAI_DATA_ROOT must be an absolute path outside the repository."
    failures=$((failures + 1))
  fi
  if ! require_backup_root "$backup" "$root"; then
    warn "ORYXENAI_BACKUP_DIR must be an absolute path outside the data root and repository."
    failures=$((failures + 1))
  fi
  if [[ "$docker_ready" == 1 ]]; then
    if ! storage_ownership_check "$root"; then
      failures=$((failures + 1))
    fi
    if ! storage_disk_check "$root"; then
      failures=$((failures + 1))
    fi
    if [[ ! -d "$backup" ]]; then
      warn "Backup directory is missing: $backup (run storage-init)."
      failures=$((failures + 1))
    fi
  fi

  if [[ "$docker_ready" == 1 && -f "$ENV_FILE" ]]; then
    if ! compose config --quiet; then
      warn "Merged production Compose configuration is invalid."
      failures=$((failures + 1))
    else
      info "Merged production Compose configuration is valid."
    fi
  fi

  if (( failures > 0 )); then
    return 1
  fi
  info "Doctor checks passed."
}

backup_database() {
  local postgres_id backup_dir destination
  backup_dir="$(backup_root)"
  run_as_root install -d -m 0700 -o "$(id -u)" -g "$(id -g)" "$backup_dir"

  postgres_id="$(compose ps -q postgres 2>/dev/null || true)"
  if [[ -z "$postgres_id" ]]; then
    info "No existing PostgreSQL container; skipping first-deploy backup."
    return
  fi

  if [[ "$(docker_cmd inspect -f '{{.State.Status}}' "$postgres_id" 2>/dev/null || true)" != "running" ]]; then
    info "PostgreSQL is not running yet; skipping first-deploy backup."
    return
  fi

  destination="$backup_dir/oryxenai-db-$(date -u +%Y%m%d-%H%M%S).sql.gz"
  info "Creating PostgreSQL backup at $destination."
  compose exec -T postgres pg_dump -U oryxen -d oryxenai | gzip >"$destination"
  chmod 600 "$destination"
  sha256sum "$destination" >"$destination.sha256"
  chmod 600 "$destination.sha256"
}

backup_filesystem() {
  local root backup_dir parent base destination temporary
  root="$(data_root)"
  backup_dir="$(backup_root)"
  [[ -d "$root" ]] || {
    info "VM data root does not exist yet; skipping filesystem backup."
    return
  }
  run_as_root install -d -m 0700 -o "$(id -u)" -g "$(id -g)" "$backup_dir"
  parent="$(dirname "$root")"
  base="$(basename "$root")"
  destination="$backup_dir/oryxenai-storage-$(date -u +%Y%m%d-%H%M%S).tar.gz"
  temporary="$destination.partial"
  info "Creating VM storage backup at $destination (PostgreSQL data is excluded; use the SQL dump)."
  run_as_root tar \
    --exclude="$base/postgres" \
    --exclude="$base/backups" \
    -C "$parent" -czf "$temporary" "$base"
  run_as_root chown "$(id -u):$(id -g)" "$temporary"
  mv "$temporary" "$destination"
  chmod 600 "$destination"
  sha256sum "$destination" >"$destination.sha256"
  chmod 600 "$destination.sha256"
}

backup_all() {
  local root backup
  root="$(data_root)"
  backup="$(backup_root)"
  require_absolute_storage_root "$root" || \
    die "ORYXENAI_DATA_ROOT must be an absolute path other than / and outside the repository."
  require_backup_root "$backup" "$root" || \
    die "ORYXENAI_BACKUP_DIR must be an absolute path outside the data root and repository."
  backup_database
  backup_filesystem
}

restore_dry_run() {
  local source="$1" checksum
  [[ -n "$source" ]] || die "Usage: restore-dry-run <backup.sql.gz|storage.tar.gz>"
  [[ -f "$source" ]] || die "Backup file not found: $source"

  case "$source" in
    *.sql.gz) gzip -t "$source" || die "PostgreSQL backup gzip validation failed." ;;
    *.tar.gz) tar -tzf "$source" >/dev/null || die "VM storage archive validation failed." ;;
    *) die "Unsupported backup type; expected .sql.gz or .tar.gz." ;;
  esac

  checksum="$source.sha256"
  if [[ -f "$checksum" ]]; then
    (cd "$(dirname "$source")" && sha256sum -c "$(basename "$checksum")" >/dev/null) || \
      die "Backup checksum validation failed."
  fi
  info "Restore dry run passed for $source; no live files or database rows were changed."
}

wait_for_migration() {
  local migration_id exit_code
  migration_id="$(compose ps -a -q migrate)"
  [[ -n "$migration_id" ]] || die "Migration container was not created."
  docker_cmd wait "$migration_id" >/dev/null
  exit_code="$(docker_cmd inspect -f '{{.State.ExitCode}}' "$migration_id")"
  [[ "$exit_code" == "0" ]] || {
    compose logs --tail 250 migrate >&2 || true
    die "Database migration failed with exit code $exit_code."
  }
}

runtime_services() {
  compose config --services \
    | grep -Ev '^(postgres|migrate)$'
}

start_release() {
  local sha="$1"
  export ORYXENAI_IMAGE_TAG="$sha"

  info "Preparing persistent VM storage."
  initialize_storage

  info "Building application image $sha."
  compose build

  info "Warming and proving the offline npm cache."
  compose run --rm --no-deps worker bash /app/scripts/warm-npm-cache.sh

  info "Running database migrations."
  compose up -d --force-recreate postgres migrate
  wait_for_migration

  mapfile -t services < <(runtime_services)
  [[ ${#services[@]} -gt 0 ]] || die "No runtime services were found in Compose."
  info "Starting runtime services: ${services[*]}"
  compose up -d --wait --wait-timeout 1800 "${services[@]}"
}

storage_smoke() {
  local stamp key artifact_kind
  stamp="$(date -u +%Y%m%dT%H%M%SZ)-$$"
  key="ops-smoke/$stamp.txt"
  artifact_kind="ops-smoke-$stamp"
  info "Testing worker artifact write/read-back and shared preview write/read-back."

  compose exec -T worker python -c \
    "import asyncio; from oryxenai.storage.code_generator_artifacts import LocalFsCodeGeneratorArtifactRepository; r=LocalFsCodeGeneratorArtifactRepository('/app/.workspace/code-generator-artifacts'); ref=asyncio.run(r.put(artifact_kind='$artifact_kind', data=b'oryxenai-storage-smoke', expires_at='2099-01-01T00:00:00+00:00')); assert asyncio.run(r.get(ref)) == b'oryxenai-storage-smoke'"
  compose exec -T worker python -c \
    "import asyncio; from oryxenai.storage.preview import LocalPreviewStorage; from pathlib import Path; s=LocalPreviewStorage(Path('/app/.workspace/code-generator-preview')); asyncio.run(s.put_immutable(key='$key', data=b'oryxenai-preview-smoke', content_type='text/plain')); item=asyncio.run(s.get('$key')); assert item is not None and item[1] == b'oryxenai-preview-smoke'"
  compose exec -T preview-gateway python -c \
    "import asyncio; from oryxenai.storage.preview import LocalPreviewStorage; from pathlib import Path; item=asyncio.run(LocalPreviewStorage(Path('/app/.workspace/code-generator-preview')).get('$key')); assert item is not None and item[1] == b'oryxenai-preview-smoke'"
  compose exec -T worker python -c \
    "import asyncio; import shutil; from pathlib import Path; from oryxenai.storage.preview import LocalPreviewStorage; shutil.rmtree(Path('/app/.workspace/code-generator-artifacts') / '$artifact_kind', ignore_errors=True); asyncio.run(LocalPreviewStorage(Path('/app/.workspace/code-generator-preview')).delete('$key'))"
  info "VM-local artifact and shared preview read-back passed."
}

credential_free_logs() {
  local log_file key value leaks=0
  log_file="$(mktemp)"
  if ! compose logs --no-color --tail 10000 >"$log_file" 2>/dev/null; then
    rm -f "$log_file"
    warn "Could not collect Compose logs for the credential scan."
    return 1
  fi

  while IFS= read -r key; do
    [[ -n "$key" ]] || continue
    value="$(env_value "$key" 2>/dev/null || true)"
    [[ -n "$value" ]] || continue
    if grep -Fq -- "$value" "$log_file"; then
      warn "Credential value for $key was found in Compose logs."
      leaks=$((leaks + 1))
    fi
  done < <(
    {
      printf '%s\n' POSTGRES_PASSWORD SUPABASE_PUBLISHABLE_KEY SUPABASE_SECRET_KEY
      active_model_keys
      awk -F= '/^[A-Z][A-Z0-9_]*(_KEY|_SECRET|_PASSWORD|_TOKEN|_CREDENTIAL_JSON)=/ { print $1 }' \
        "$ENV_FILE" 2>/dev/null || true
    } | sort -u
  )
  rm -f "$log_file"
  if (( leaks > 0 )); then
    return 1
  fi
  info "Compose log credential scan passed without printing credential values."
}

verify_internal() {
  info "Checking internal HTTP endpoints and Caddy configuration."
  compose exec -T app python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live').read(); urllib.request.urlopen('http://127.0.0.1:8000/health/ready').read()"
  compose exec -T preview-gateway python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4174/health/live').read(); urllib.request.urlopen('http://127.0.0.1:4174/health/ready').read()"
  compose exec -T caddy caddy validate \
    --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null
  storage_smoke
  credential_free_logs
  info "Internal health checks passed."
}

verify_external() {
  local app_host preview_host
  app_host="$(env_value APP_HOST)"
  preview_host="$(env_value PREVIEW_HOST)"
  info "Checking public HTTPS endpoints."
  curl -fsS --max-time 30 "https://$app_host/health/live" >/dev/null
  curl -fsS --max-time 30 "https://$app_host/health/ready" >/dev/null
  curl -fsS --max-time 30 "https://$preview_host/health/live" >/dev/null
  info "Public HTTPS checks passed."
}

resolve_release() {
  local requested="${1:-}"
  local branch ref

  git status --porcelain --untracked-files=no | grep -q . && \
    die "The VM checkout has tracked changes; commit or restore them before deploying."

  if [[ -z "$requested" ]]; then
    branch="$(deployment_branch)"
    info "Fetching deployment branch $branch." >&2
    git fetch origin "$branch" --prune
    ref="origin/$branch"
  elif [[ "$requested" =~ ^[0-9a-fA-F]{7,40}$ ]]; then
    git fetch origin --prune
    ref="$requested"
    branch="$(deployment_branch)"
  else
    branch="$requested"
    git fetch origin "$branch" --prune
    ref="origin/$branch"
  fi

  git rev-parse "$ref^{commit}"
}

deploy() {
  local requested="${1:-}"
  local sha previous branch

  [[ -f "$ENV_FILE" ]] || die "Missing .env; run setup first."
  [[ -f "$PRODUCTION_LOCAL" ]] || render_production_config
  doctor

  if [[ -n "$requested" ]] && [[ ! "$requested" =~ ^[0-9a-fA-F]{7,40}$ ]]; then
    branch="$requested"
  else
    branch="$(deployment_branch)"
  fi
  sha="$(resolve_release "$requested")"
  previous="$(state_value LAST_GOOD_SHA 2>/dev/null || true)"

  info "Checking out release $sha."
  git checkout --detach "$sha"
  backup_all
  start_release "$sha"
  verify_internal
  write_state "$sha" "${previous:-}" "$branch"
  info "Release $sha is running."
  info "Run ./scripts/azure-deploy.sh verify to check public HTTPS and OAuth prerequisites."
}

configure() {
  [[ -f "$ENV_FILE" ]] || die "Missing .env; run setup first."
  local editor="${EDITOR:-nano}"
  "$editor" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  render_production_config
  initialize_storage
  doctor
}

status() {
  compose ps
  if [[ -f "$STATE_FILE" ]]; then
    info "Deployment state:"
    cat "$STATE_FILE"
  fi
}

logs() {
  if [[ "$#" -eq 0 ]]; then
    compose logs --tail 250
  else
    compose logs --tail 250 "$@"
  fi
}

rollback() {
  local current target branch
  current="$(state_value LAST_GOOD_SHA 2>/dev/null || true)"
  target="$(state_value PREVIOUS_GOOD_SHA 2>/dev/null || true)"
  branch="$(deployment_branch)"
  [[ -n "$current" && -n "$target" ]] || die "There is no previous release recorded yet."

  git status --porcelain --untracked-files=no | grep -q . && \
    die "The VM checkout has tracked changes; commit or restore them before rolling back."
  git checkout --detach "$target"
  info "Rolling back from $current to $target."
  backup_all
  start_release "$target"
  verify_internal
  write_state "$target" "$current" "$branch"
  info "Rollback completed. Check public HTTPS with verify."
}

usage() {
  cat <<'EOF'
Usage:
  ./scripts/azure-deploy.sh setup
  ./scripts/azure-deploy.sh configure
  ./scripts/azure-deploy.sh doctor
  ./scripts/azure-deploy.sh deploy [commit-sha-or-branch]
  ./scripts/azure-deploy.sh status
  ./scripts/azure-deploy.sh logs [service...]
  ./scripts/azure-deploy.sh verify
  ./scripts/azure-deploy.sh backup
  ./scripts/azure-deploy.sh storage-init
  ./scripts/azure-deploy.sh disk-check
  ./scripts/azure-deploy.sh storage-smoke
  ./scripts/azure-deploy.sh restore-dry-run <backup-file>
  ./scripts/azure-deploy.sh rollback
EOF
}

command="${1:-}"
shift || true

case "$command" in
  setup)
    install_docker
    write_initial_env
    initialize_storage
    doctor
    ;;
  configure)
    configure
    ;;
  doctor)
    doctor
    ;;
  deploy)
    deploy "${1:-}"
    ;;
  status)
    status
    ;;
  logs)
    logs "$@"
    ;;
  verify)
    verify_internal
    verify_external
    ;;
  backup)
    backup_all
    ;;
  storage-init)
    initialize_storage
    ;;
  disk-check)
    storage_disk_check "$(data_root)"
    ;;
  storage-smoke)
    storage_smoke
    ;;
  restore-dry-run)
    restore_dry_run "${1:-}"
    ;;
  rollback)
    rollback
    ;;
  help|-h|--help|"")
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
