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
CREATED_TARGETS=()
CREATED_SOURCES=()
CREATED_LINK_IDENTITIES=()

PYTHON=""
for python_candidate in python3 python; do
  if command -v "$python_candidate" >/dev/null 2>&1; then
    candidate_path="$(command -v "$python_candidate")"
    if "$candidate_path" -c \
      'import sys; raise SystemExit(not ((3, 11) <= sys.version_info < (3, 14)))' \
      >/dev/null 2>&1; then
      PYTHON="$candidate_path"
      break
    fi
  fi
done
if [[ -z "$PYTHON" ]]; then
  echo "Python 3.11 through 3.13 is required to install Brave Search Pro." >&2
  exit 1
fi

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

rollback_created_links() {
  local index target source link_identity

  for ((index = ${#CREATED_TARGETS[@]} - 1; index >= 0; index--)); do
    target="${CREATED_TARGETS[$index]}"
    source="${CREATED_SOURCES[$index]}"
    link_identity="${CREATED_LINK_IDENTITIES[$index]}"

    # Only remove the exact symlink this invocation created. If another process
    # replaced it, leave that path untouched.
    if "$PYTHON" - "$target" "$source" "$link_identity" <<'PY'
import os
import sys

target, source, expected_identity = sys.argv[1:]
try:
    status = os.lstat(target)
except FileNotFoundError:
    raise SystemExit(1)

if (
    not os.path.islink(target)
    or os.readlink(target) != source
    or f"{status.st_dev}:{status.st_ino}" != expected_identity
):
    raise SystemExit(1)

os.unlink(target)
PY
    then
      echo "Rolled back: $target"
    fi
  done
}

create_symlink() {
  local source="$1"
  local target="$2"

  "$PYTHON" - "$source" "$target" <<'PY'
import os
import sys

source, target = sys.argv[1:]
try:
    os.symlink(source, target)
except FileExistsError:
    raise SystemExit(1)
except OSError as error:
    print(f"Unable to create symlink at {target}: {error}", file=sys.stderr)
    raise SystemExit(1)

status = os.lstat(target)
print(f"{status.st_dev}:{status.st_ino}")
PY
}

install_target() {
  local target="$1"
  local source="$2"
  local current_target
  local link_identity

  # Preflight is not enough: another process can create a path after the
  # initial check and before this target is installed.
  if ! preflight_target "$target" "$source"; then
    return 1
  fi

  if [[ -e "$target" || -L "$target" ]]; then
    current_target="$(readlink "$target" 2>/dev/null || true)"
    echo "Already installed: $target -> $current_target"
  else
    if ! link_identity="$(create_symlink "$source" "$target")"; then
      # Report a useful conflict if the destination appeared after the
      # install-time check. Do not overwrite or remove that conflicting path.
      if [[ -e "$target" || -L "$target" ]]; then
        preflight_target "$target" "$source" || true
      fi
      echo "Unable to install plugin path: $target" >&2
      return 1
    fi
    CREATED_TARGETS+=("$target")
    CREATED_SOURCES+=("$source")
    CREATED_LINK_IDENTITIES+=("$link_identity")
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
if ! install_target "$BACKEND_TARGET_DIR" "$REPO_ROOT"; then
  rollback_created_links
  exit 1
fi
if ! install_target "$DESKTOP_TARGET_DIR" "$REPO_ROOT/desktop"; then
  rollback_created_links
  exit 1
fi

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
printf '  HERMES_HOME=%q %q %q\n' \
  "$HERMES_BASE" "$PYTHON" "$BACKEND_TARGET_DIR/scripts/doctor.py"
