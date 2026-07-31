#!/usr/bin/env bash
set -euo pipefail

PLUGIN_DIR_NAME="brave-search"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_ROOT="${HERMES_HOME:-$HOME/.hermes}"
PROFILE=""

if [[ -n "${HERMES_PROFILE:-}" ]]; then
  PROFILE="${HERMES_PROFILE,,}"
  if [[ ! "$PROFILE" =~ ^[a-z0-9][a-z0-9_-]{0,63}$ ]]; then
    printf 'Invalid Hermes profile name: %q\n' "$HERMES_PROFILE" >&2
    exit 1
  fi
  case "$PROFILE" in
    hermes|test|tmp|root|sudo)
      printf 'Reserved Hermes profile name: %q\n' "$HERMES_PROFILE" >&2
      exit 1
      ;;
  esac
fi

if [[ -z "$PROFILE" || "$PROFILE" == "default" ]]; then
  HERMES_BASE="$HERMES_ROOT"
else
  HERMES_BASE="$HERMES_ROOT/profiles/$PROFILE"
fi

TARGET_DIR="$HERMES_BASE/plugins/$PLUGIN_DIR_NAME"
CONFIG_PATH="$HERMES_BASE/config.yaml"

print_hermes_step() {
  local command="$1"
  printf '  '
  if [[ -n "${HERMES_HOME:-}" ]]; then
    printf 'HERMES_HOME=%q ' "$HERMES_ROOT"
  fi
  printf 'hermes'
  if [[ -n "$PROFILE" ]]; then
    printf ' --profile %q' "$PROFILE"
  fi
  printf ' %s\n' "$command"
}

mkdir -p "$(dirname "$TARGET_DIR")"

if [[ -e "$TARGET_DIR" || -L "$TARGET_DIR" ]]; then
  CURRENT_TARGET="$(readlink "$TARGET_DIR" 2>/dev/null || true)"
  if [[ "$CURRENT_TARGET" == "$REPO_ROOT" ]]; then
    echo "Already installed: $TARGET_DIR -> $REPO_ROOT"
  else
    echo "Refusing to overwrite existing plugin path: $TARGET_DIR" >&2
    echo "Remove it first, or install with:" >&2
    print_hermes_step \
      "plugins install GodsBoy/hermes-brave-search-pro --force --no-enable" >&2
    exit 1
  fi
else
  ln -s "$REPO_ROOT" "$TARGET_DIR"
  echo "Installed: $TARGET_DIR -> $REPO_ROOT"
fi

cat <<EOF

Next steps:
EOF
print_hermes_step "plugins enable brave-search --allow-tool-override"
print_hermes_step "gateway restart"
cat <<EOF

Then add your Brave key to the environment Hermes runs with:
  BRAVE_SEARCH_API_KEY=bsa-your-key-here

And set search/extract backends in $CONFIG_PATH:
  web:
    backend: "brave-pro"
    search_backend: "brave-pro"
    extract_backend: "tavily"

Run the profile-scoped doctor:
EOF
printf '  HERMES_HOME=%q python %q\n' \
  "$HERMES_BASE" "$TARGET_DIR/scripts/doctor.py"
