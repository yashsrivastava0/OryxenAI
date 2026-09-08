#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
scaffold="$repo_root/src/oryxenai/agents/code_generator/scaffolds/react-vite-v1"
cache="${NPM_CACHE_ROOT:-$repo_root/.workspace/npm-cache}"
mkdir -p "$cache"

pushd "$scaffold" >/dev/null
popd >/dev/null

# Read package pins from the authoritative TOML without hardcoding a package
# list in this operational script. Install the complete merged graph in a
# disposable project so npm caches tarballs and transitive/platform packages,
# not just registry metadata.
warm="$repo_root/.workspace/npm-cache-warm"
rm -rf "$warm"
mkdir -p "$warm"
cp "$scaffold/package.json" "$scaffold/package-lock.json" "$warm/"
mapfile -t configured_packages < <(
awk '
  /^\[code_generator_dependencies\.supported_packages\./ {
    section=$0; sub(/^.*supported_packages\./, "", section); sub(/\].*$/, "", section); gsub(/"/, "", section); next
  }
  section != "" && /^version_pin[[:space:]]*=/ {
    version=$0; sub(/^[^=]*=[[:space:]]*"/, "", version); sub(/".*$/, "", version)
    print section "@" version; section=""
  }
' "$repo_root/config/app.toml" | while IFS= read -r package; do
  printf '%s\n' "$package"
done
)
pushd "$warm" >/dev/null
npm install --cache "$cache" --ignore-scripts --no-audit --no-fund "${configured_packages[@]}"
popd >/dev/null

proof="$(mktemp -d "$repo_root/.workspace/npm-cache-proof.XXXXXX")"
cp "$warm/package.json" "$warm/package-lock.json" "$proof/"
trap 'rm -rf "$proof" "$warm"' EXIT
cd "$proof"
npm ci --cache "$cache" --ignore-scripts --offline --no-audit --no-fund
echo "Offline npm cache warmed and proven at $cache"
