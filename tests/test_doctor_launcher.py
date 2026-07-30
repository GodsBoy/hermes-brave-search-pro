from __future__ import annotations

import importlib.util
import subprocess
import sys
import venv
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "doctor.py"
POLYGLOT = (
    "#!/bin/sh\n"
    "'''exec' \"$(dirname -- \"$(realpath -- \"$0\")\")\"/"
    "'python3' \"$0\" \"$@\"\n"
    "' '''\n"
)


def _load_doctor():
    spec = importlib.util.spec_from_file_location("doctor_script_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _python_link(path: Path) -> Path:
    path.symlink_to(sys.executable)
    return path


def _launcher(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.fixture
def doctor():
    return _load_doctor()


def test_resolves_direct_python_shebang(doctor, tmp_path):
    interpreter = _python_link(tmp_path / "python3")
    launcher = _launcher(tmp_path / "hermes", f"#!{interpreter}\n")

    assert doctor._resolve_launcher_interpreter(launcher) == str(interpreter)


def test_resolves_env_python_shebang(doctor, monkeypatch, tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    interpreter = _python_link(bin_dir / "python3")
    monkeypatch.setenv("PATH", str(bin_dir))
    launcher = _launcher(tmp_path / "hermes", "#!/usr/bin/env python3\n")

    assert doctor._resolve_launcher_interpreter(launcher) == str(interpreter)


def test_resolves_current_polyglot_launcher(doctor, tmp_path):
    interpreter = _python_link(tmp_path / "python3")
    launcher = _launcher(tmp_path / "hermes", POLYGLOT)

    assert doctor._resolve_launcher_interpreter(launcher) == str(interpreter)


def test_preserves_virtualenv_interpreter_path(doctor, tmp_path):
    venv_dir = tmp_path / "venv"
    venv.EnvBuilder(with_pip=False).create(venv_dir)
    interpreter = venv_dir / "bin" / "python3"
    launcher = _launcher(venv_dir / "bin" / "hermes", POLYGLOT)

    resolved = doctor._resolve_launcher_interpreter(launcher)

    assert resolved == str(interpreter)
    result = subprocess.run(
        [resolved, "-c", "import sys; print(sys.prefix)"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert Path(result.stdout.strip()) == venv_dir


def test_resolves_polyglot_sibling_after_launcher_symlink(doctor, tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    interpreter = _python_link(real_dir / "python3")
    real_launcher = _launcher(real_dir / "hermes", POLYGLOT)
    launcher = tmp_path / "hermes"
    launcher.symlink_to(real_launcher)

    assert doctor._resolve_launcher_interpreter(launcher) == str(interpreter)


@pytest.mark.parametrize(
    "content",
    [
        "#!/bin/bash\n",
        "#!/usr/bin/env bash\n",
        "#!/usr/bin/python3 -I\n",
        "#!/usr/bin/env python3 -I\n",
        "#!/bin/sh\necho unsupported\n",
    ],
)
def test_rejects_unsupported_launchers(doctor, tmp_path, content):
    launcher = _launcher(tmp_path / "hermes", content)

    assert doctor._resolve_launcher_interpreter(launcher) is None


@pytest.mark.parametrize(
    "content",
    [
        "",
        "#!\n",
        "#!/usr/bin/env\n",
        "#!/usr/bin/env -S\n",
        "#!\"unterminated\n",
    ],
)
def test_rejects_malformed_launchers(doctor, tmp_path, content):
    launcher = _launcher(tmp_path / "hermes", content)

    assert doctor._resolve_launcher_interpreter(launcher) is None


def test_rejects_missing_direct_interpreter(doctor, tmp_path):
    launcher = _launcher(tmp_path / "hermes", f"#!{tmp_path / 'python3'}\n")

    assert doctor._resolve_launcher_interpreter(launcher) is None


def test_rejects_missing_polyglot_sibling(doctor, tmp_path):
    launcher = _launcher(tmp_path / "hermes", POLYGLOT)

    assert doctor._resolve_launcher_interpreter(launcher) is None


def test_rejects_unreadable_launcher(doctor, monkeypatch, tmp_path):
    launcher = _launcher(tmp_path / "hermes", POLYGLOT)

    def raise_permission(*args, **kwargs):
        raise PermissionError("launcher cannot be read")

    monkeypatch.setattr(Path, "open", raise_permission)

    assert doctor._resolve_launcher_interpreter(launcher) is None


def test_rejects_non_file_launcher_before_opening(doctor, monkeypatch, tmp_path):
    launcher = _launcher(tmp_path / "hermes", POLYGLOT)
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    monkeypatch.setattr(
        Path,
        "open",
        lambda *args, **kwargs: pytest.fail("non-file launcher must not be opened"),
    )

    assert doctor._resolve_launcher_interpreter(launcher) is None


def test_rejects_non_executable_python(doctor, tmp_path):
    interpreter = tmp_path / "python3"
    interpreter.write_text("not executable\n", encoding="utf-8")
    launcher = _launcher(tmp_path / "hermes", f"#!{interpreter}\n")

    assert doctor._resolve_launcher_interpreter(launcher) is None


def test_infers_named_profile_home_from_installed_path(doctor, tmp_path):
    profile_home = tmp_path / ".hermes" / "profiles" / "work"
    script = profile_home / "plugins" / "brave-search" / "scripts" / "doctor.py"

    assert doctor._installed_hermes_home(script) == profile_home


def test_does_not_infer_home_from_checkout_path(doctor, tmp_path):
    script = tmp_path / "brave" / "scripts" / "doctor.py"

    assert doctor._installed_hermes_home(script) is None


def test_sets_inferred_hermes_home(doctor, monkeypatch, tmp_path):
    inferred_home = tmp_path / "profile"
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setattr(doctor, "_installed_hermes_home", lambda: inferred_home)

    doctor._set_installed_hermes_home()

    assert doctor.os.environ["HERMES_HOME"] == str(inferred_home)


def test_preserves_explicit_hermes_home(doctor, monkeypatch, tmp_path):
    explicit_home = tmp_path / "explicit"
    monkeypatch.setenv("HERMES_HOME", str(explicit_home))
    monkeypatch.setattr(
        doctor,
        "_installed_hermes_home",
        lambda: tmp_path / "inferred",
    )

    doctor._set_installed_hermes_home()

    assert doctor.os.environ["HERMES_HOME"] == str(explicit_home)


def test_returns_none_when_hermes_is_absent(doctor, monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)

    assert doctor._hermes_python() is None


def test_reexec_uses_resolved_polyglot_interpreter(doctor, monkeypatch, tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    interpreter = real_dir / "python3"
    interpreter.write_text(f"#!{sys.executable}\n", encoding="utf-8")
    interpreter.chmod(0o755)
    real_launcher = _launcher(real_dir / "hermes", POLYGLOT)
    launcher = tmp_path / "hermes"
    launcher.symlink_to(real_launcher)
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.setattr(doctor.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(doctor.sys, "argv", [str(SCRIPT), "--fix"])
    calls = []
    monkeypatch.setattr(
        doctor.os,
        "execv",
        lambda path, arguments: calls.append((path, arguments)),
    )

    doctor._reexec_with_hermes_python()

    expected = str(interpreter)
    assert calls == [(expected, [expected, str(SCRIPT), "--fix"])]


def test_reexec_ignores_unusable_interpreter(doctor, monkeypatch, tmp_path):
    interpreter = _launcher(tmp_path / "python3", "not a Python executable\n")
    monkeypatch.setattr(doctor.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(doctor, "_hermes_python", lambda: str(interpreter))
    monkeypatch.setattr(
        doctor.os,
        "execv",
        lambda *args: (_ for _ in ()).throw(OSError("exec format error")),
    )

    doctor._reexec_with_hermes_python()


def test_reexec_does_not_skip_virtualenv_symlink(doctor, monkeypatch, tmp_path):
    interpreter = _python_link(tmp_path / "python3")
    monkeypatch.setattr(doctor.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(doctor, "_hermes_python", lambda: str(interpreter))
    calls = []
    monkeypatch.setattr(
        doctor.os,
        "execv",
        lambda path, arguments: calls.append((path, arguments)),
    )

    doctor._reexec_with_hermes_python()

    assert calls == [
        (str(interpreter), [str(interpreter), *doctor.sys.argv]),
    ]


def test_reexec_does_not_loop_on_current_interpreter(doctor, monkeypatch):
    monkeypatch.setattr(doctor.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(doctor, "_hermes_python", lambda: sys.executable)
    monkeypatch.setattr(
        doctor.os,
        "execv",
        lambda *args: pytest.fail("current interpreter must not be re-execed"),
    )

    doctor._reexec_with_hermes_python()
