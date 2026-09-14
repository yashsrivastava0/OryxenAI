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
BACKUP_DIR="${ORYXENAI_BACKUP_DIR:-$HOME/oryxenai-backups}"
DEFAULT_BRANCH="codex/code-generator-control-room"

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
    -f "$REPO_ROOT/compose.yaml" \
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

  local app_host preview_host account_id bucket temporary
  app_host="$(env_value APP_HOST 2>/dev/null || true)"
  preview_host="$(env_value PREVIEW_HOST 2>/dev/null || true)"
  account_id="$(env_value R2_ACCOUNT_ID 2>/dev/null || true)"
  bucket="$(env_value R2_BUCKET 2>/dev/null || true)"

  [[ -n "$app_host" ]] || die "APP_HOST is missing from .env"
  [[ -n "$preview_host" ]] || die "PREVIEW_HOST is missing from .env"
  [[ -n "$account_id" ]] || die "R2_ACCOUNT_ID is missing from .env"
  [[ -n "$bucket" ]] || die "R2_BUCKET is missing from .env"

  temporary="$(mktemp "$REPO_ROOT/config/app.production.local.toml.XXXXXX")"
  sed \
    -e "s|<APP_HOST>|$(sed_escape "$app_host")|g" \
    -e "s|<PREVIEW_HOST>|$(sed_escape "$preview_host")|g" \
    -e "s|<ACCOUNT_ID>|$(sed_escape "$account_id")|g" \
    -e "s|<R2_BUCKET>|$(sed_escape "$bucket")|g" \
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
  ask_required "Cloudflare R2 account ID"
  set_env_value R2_ACCOUNT_ID "$REPLY"
  ask_required "Cloudflare R2 bucket name"
  set_env_value R2_BUCKET "$REPLY"
  ask_required_secret "Cloudflare R2 access key ID"
  set_env_value R2_ACCESS_KEY_ID "$REPLY"
  ask_required_secret "Cloudflare R2 secret access key"
  set_env_value R2_SECRET_ACCESS_KEY "$REPLY"

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
  local key value host free_kib
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
      R2_ACCOUNT_ID \
      R2_BUCKET \
      R2_ACCESS_KEY_ID \
      R2_SECRET_ACCESS_KEY \
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

  if [[ -f "$PRODUCTION_LOCAL" ]] && grep -Eq '<(APP_HOST|PREVIEW_HOST|ACCOUNT_ID|R2_BUCKET)>' "$PRODUCTION_LOCAL"; then
    warn "Production configuration still contains placeholders."
    failures=$((failures + 1))
  fi

  if command -v docker >/dev/null 2>&1 && docker_cmd info >/dev/null 2>&1 && [[ -f "$ENV_FILE" ]]; then
    if ! compose config --quiet; then
      warn "Merged production Compose configuration is invalid."
      failures=$((failures + 1))
    else
      info "Merged production Compose configuration is valid."
    fi
  fi

  if command -v df >/dev/null 2>&1; then
    free_kib="$(df -Pk "$REPO_ROOT" | awk 'NR==2 { print $4 }')"
    if [[ "$free_kib" =~ ^[0-9]+$ ]] && (( free_kib < 10485760 )); then
      warn "Less than 10 GiB is free on the deployment disk."
    fi
  fi

  if (( failures > 0 )); then
    return 1
  fi
  info "Doctor checks passed."
}

backup_database() {
  local postgres_id
  mkdir -p "$BACKUP_DIR"
  chmod 700 "$BACKUP_DIR"

  postgres_id="$(compose ps -q postgres 2>/dev/null || true)"
  if [[ -z "$postgres_id" ]]; then
    info "No existing PostgreSQL container; skipping first-deploy backup."
    return
  fi

  if [[ "$(docker_cmd inspect -f '{{.State.Status}}' "$postgres_id" 2>/dev/null || true)" != "running" ]]; then
    info "PostgreSQL is not running yet; skipping first-deploy backup."
    return
  fi

  local destination="$BACKUP_DIR/oryxenai-$(date -u +%Y%m%d-%H%M%S).sql.gz"
  info "Creating PostgreSQL backup at $destination."
  compose exec -T postgres pg_dump -U oryxen -d oryxenai | gzip >"$destination"
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
    | grep -Ev '^(postgres|migrate|build-validation|codegen-cache-warm)$'
}

start_release() {
  local sha="$1"
  export ORYXENAI_IMAGE_TAG="$sha"

  info "Building application image $sha."
  compose build

  info "Warming and proving the offline npm cache."
  compose --profile codegen-cache run --rm codegen-cache-warm

  info "Running database migrations."
  compose up -d --force-recreate postgres migrate
  wait_for_migration

  mapfile -t services < <(runtime_services)
  [[ ${#services[@]} -gt 0 ]] || die "No runtime services were found in Compose."
  info "Starting runtime services: ${services[*]}"
  compose up -d --wait --wait-timeout 1800 "${services[@]}"
}

verify_internal() {
  info "Checking internal HTTP endpoints."
  curl -fsS --max-time 30 http://127.0.0.1:8000/health/live >/dev/null
  curl -fsS --max-time 30 http://127.0.0.1:8000/health/ready >/dev/null
  curl -fsS --max-time 30 http://127.0.0.1:4174/health/live >/dev/null
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
  backup_database
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
  ./scripts/azure-deploy.sh rollback
EOF
}

command="${1:-}"
shift || true

case "$command" in
  setup)
    install_docker
    write_initial_env
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
    backup_database
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
