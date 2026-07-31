#!/usr/bin/env python3
"""Run Brave Search Pro doctor checks from a git plugin checkout."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import sys
from pathlib import Path

_POLYGLOT_SHEBANG = "#!/bin/sh"
_POLYGLOT_EXEC = (
    "'''exec' \"$(dirname -- \"$(realpath -- \"$0\")\")\"/"
    "'python3' \"$0\" \"$@\""
)
_PYTHON_NAME = re.compile(r"python(?:3(?:\.\d+)?)?$")


def _is_executable(path: Path) -> Path | None:
    """Validate the target while preserving virtualenv launcher semantics."""

    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        return None
    return path.absolute()


def _python_executable(path: Path) -> str | None:
    if not _PYTHON_NAME.fullmatch(path.name):
        return None
    resolved = _is_executable(path)
    return str(resolved) if resolved else None


def _env_python(tokens: list[str]) -> str | None:
    if not tokens:
        return None
    env = _is_executable(Path(tokens[0]))
    if env is None or env.name != "env":
        return None

    arguments = tokens[1:]
    if arguments and arguments[0] == "-S":
        arguments = arguments[1:]
    if len(arguments) != 1 or arguments[0].startswith("-"):
        return None

    candidate = arguments[0]
    if "/" in candidate:
        path = Path(candidate)
        return _python_executable(path) if path.is_absolute() else None
    if not _PYTHON_NAME.fullmatch(candidate):
        return None

    interpreter = shutil.which(candidate)
    return _python_executable(Path(interpreter)) if interpreter else None


def _shebang_python(first_line: str) -> str | None:
    if not first_line.startswith("#!"):
        return None
    try:
        tokens = shlex.split(first_line[2:].strip())
    except ValueError:
        return None
    if not tokens:
        return None

    if Path(tokens[0]).name == "env":
        return _env_python(tokens)
    if len(tokens) != 1 or not Path(tokens[0]).is_absolute():
        return None
    return _python_executable(Path(tokens[0]))


def _resolve_launcher_interpreter(launcher: str | Path) -> str | None:
    """Resolve a supported Hermes launcher to its real Python interpreter."""

    try:
        launcher_path = Path(launcher).resolve(strict=True)
        if not launcher_path.is_file():
            return None
        with launcher_path.open(encoding="utf-8") as source:
            first_line = source.readline().rstrip("\r\n")
            second_line = source.readline().rstrip("\r\n")
    except (OSError, UnicodeDecodeError, RuntimeError):
        return None

    interpreter = _shebang_python(first_line)
    if interpreter:
        return interpreter
    if first_line == _POLYGLOT_SHEBANG and second_line == _POLYGLOT_EXEC:
        return _python_executable(launcher_path.parent / "python3")
    return None


def _hermes_launcher() -> str | None:
    return shutil.which("hermes")


def _hermes_python() -> str | None:
    hermes = _hermes_launcher()
    return _resolve_launcher_interpreter(hermes) if hermes else None


def _installed_hermes_home(script_path: Path | None = None) -> Path | None:
    script = (script_path or Path(__file__)).absolute()
    plugin_dir = script.parent.parent
    if plugin_dir.name != "brave-search" or plugin_dir.parent.name != "plugins":
        return None
    return plugin_dir.parent.parent


def _set_installed_hermes_home() -> None:
    if "HERMES_HOME" in os.environ:
        return
    hermes_home = _installed_hermes_home()
    if hermes_home:
        os.environ["HERMES_HOME"] = str(hermes_home)


def _reexec_with_hermes_python() -> None:
    python = _hermes_python()
    if not python:
        return
    try:
        same_interpreter = Path(python).absolute() == Path(sys.executable).absolute()
    except OSError:
        return
    if same_interpreter:
        return
    try:
        os.execv(python, [python, *sys.argv])
    except OSError:
        return


def _run() -> int:
    _set_installed_hermes_home()
    _reexec_with_hermes_python()

    src = Path(__file__).resolve().parents[1] / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from hermes_brave_search.doctor import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_run())
