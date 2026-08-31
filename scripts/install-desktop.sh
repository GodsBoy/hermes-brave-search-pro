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
    hermes|test|tmp|root)
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

TARGET_DIR="$HERMES_BASE/desktop-plugins/$PLUGIN_DIR_NAME"
SOURCE_DIR="$REPO_ROOT/desktop"

if [[ -e "$TARGET_DIR" || -L "$TARGET_DIR" ]]; then
  CURRENT_TARGET="$(readlink "$TARGET_DIR" 2>/dev/null || true)"
  if [[ "$CURRENT_TARGET" == "$SOURCE_DIR" ]]; then
    echo "Already installed: $TARGET_DIR -> $SOURCE_DIR"
  else
    echo "Refusing to overwrite existing plugin path: $TARGET_DIR" >&2
    echo "Remove the conflicting path first, then run this installer again." >&2
    exit 1
  fi
else
  mkdir -p "$(dirname "$TARGET_DIR")"
  ln -s "$SOURCE_DIR" "$TARGET_DIR"
  echo "Installed: $TARGET_DIR -> $SOURCE_DIR"
fi

cat <<EOF

Desktop surface installed for the selected local profile.

This installs only the Desktop plugin. Install and enable the Python backend
separately in the active gateway profile, then restart that gateway before use.
Open Hermes Desktop Settings and enable Brave Search. The Desktop and backend
plugins are separate toggles.
EOF
