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

BACKEND_TARGET_DIR="$HERMES_BASE/plugins/$PLUGIN_DIR_NAME"
DESKTOP_TARGET_DIR="$HERMES_BASE/desktop-plugins/$PLUGIN_DIR_NAME"
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

preflight_target() {
  local target="$1"
  local expected="$2"

  if [[ -e "$target" || -L "$target" ]]; then
    local current_target
    current_target="$(readlink "$target" 2>/dev/null || true)"
    if [[ "$current_target" != "$expected" ]]; then
      echo "Refusing to overwrite existing plugin path: $target" >&2
      if [[ "$target" == "$BACKEND_TARGET_DIR" ]]; then
        echo "Remove it first, or install with:" >&2
        print_hermes_step \
          "plugins install GodsBoy/hermes-brave-search-pro --force --no-enable" >&2
      else
        echo "Remove it first, then run this installer again." >&2
      fi
      return 1
    fi
  fi
}

install_target() {
  local target="$1"
  local source="$2"
  local current_target

  if [[ -e "$target" || -L "$target" ]]; then
    current_target="$(readlink "$target" 2>/dev/null || true)"
    echo "Already installed: $target -> $current_target"
  else
    ln -s "$source" "$target"
    echo "Installed: $target -> $source"
  fi
}

# Check both destinations before creating either link. A conflict in one
# profile-scoped surface must not leave the other surface partially installed.
if ! preflight_target "$BACKEND_TARGET_DIR" "$REPO_ROOT" || \
  ! preflight_target "$DESKTOP_TARGET_DIR" "$REPO_ROOT/desktop"; then
  exit 1
fi

mkdir -p "$(dirname "$BACKEND_TARGET_DIR")" "$(dirname "$DESKTOP_TARGET_DIR")"
install_target "$BACKEND_TARGET_DIR" "$REPO_ROOT"
install_target "$DESKTOP_TARGET_DIR" "$REPO_ROOT/desktop"

cat <<EOF

Next steps:
EOF
print_hermes_step "plugins enable brave-search --allow-tool-override"
print_hermes_step "gateway restart"
cat <<EOF

The backend and Desktop plugin are separate toggles. After the gateway restarts,
open Hermes Desktop Settings and enable Brave Search for this profile.

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
  "$HERMES_BASE" "$BACKEND_TARGET_DIR/scripts/doctor.py"
