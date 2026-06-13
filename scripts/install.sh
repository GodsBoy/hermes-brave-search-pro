#!/usr/bin/env bash
set -euo pipefail

PLUGIN_DIR_NAME="brave-search"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "${HERMES_PROFILE:-}" ]]; then
  HERMES_BASE="${HERMES_HOME:-$HOME/.hermes}/profiles/${HERMES_PROFILE}"
else
  HERMES_BASE="${HERMES_HOME:-$HOME/.hermes}"
fi

TARGET_DIR="${HERMES_BASE}/plugins/${PLUGIN_DIR_NAME}"

mkdir -p "$(dirname "$TARGET_DIR")"

if [[ -e "$TARGET_DIR" || -L "$TARGET_DIR" ]]; then
  CURRENT_TARGET="$(readlink "$TARGET_DIR" 2>/dev/null || true)"
  if [[ "$CURRENT_TARGET" == "$REPO_ROOT" ]]; then
    echo "Already installed: $TARGET_DIR -> $REPO_ROOT"
  else
    echo "Refusing to overwrite existing plugin path: $TARGET_DIR" >&2
    echo "Remove it first, or install with: hermes plugins install GodsBoy/hermes-brave-search-pro --force --enable" >&2
    exit 1
  fi
else
  ln -s "$REPO_ROOT" "$TARGET_DIR"
  echo "Installed: $TARGET_DIR -> $REPO_ROOT"
fi

cat <<EOF

Next steps:
  hermes plugins enable brave-search

Then add your Brave key to the environment Hermes runs with:
  BRAVE_SEARCH_API_KEY=bsa-your-key-here

And set search/extract backends in ~/.hermes/config.yaml:
  web:
    search_backend: "brave-pro"
    extract_backend: "tavily"
EOF
