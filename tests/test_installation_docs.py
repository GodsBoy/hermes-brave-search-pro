from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC_PATHS = (
    ROOT / "README.md",
    ROOT / "docs" / "installation.md",
    ROOT / "after-install.md",
    ROOT / "examples" / "config.yaml",
    ROOT / "scripts" / "install.sh",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def assert_in_order(text: str, *fragments: str) -> None:
    position = -1
    for fragment in fragments:
        next_position = text.find(fragment, position + 1)
        assert next_position >= 0, f"missing fragment: {fragment}"
        position = next_position


def test_fresh_install_guidance_grants_override_before_restart() -> None:
    for path in (ROOT / "README.md", ROOT / "docs" / "installation.md"):
        text = read(path)
        assert_in_order(
            text,
            "hermes plugins install GodsBoy/hermes-brave-search-pro --no-enable",
            "hermes plugins enable brave-search --allow-tool-override",
            "hermes gateway restart",
        )


def test_direct_and_profile_guidance_grants_override_before_restart() -> None:
    for path in (ROOT / "README.md", ROOT / "docs" / "installation.md"):
        text = read(path)
        assert_in_order(
            text,
            "git clone https://github.com/GodsBoy/hermes-brave-search-pro.git \\\n"
            "  ~/.hermes/plugins/brave-search",
            "hermes plugins enable brave-search --allow-tool-override",
            "hermes gateway restart",
            "git clone https://github.com/GodsBoy/hermes-brave-search-pro.git \\\n"
            "  ~/.hermes/profiles/myprofile/plugins/brave-search",
            "hermes plugins enable brave-search --allow-tool-override",
            "hermes gateway restart",
            "hermes --profile myprofile plugins enable "
            "brave-search --allow-tool-override",
            "hermes --profile myprofile gateway restart",
            "python ~/.hermes/profiles/myprofile/plugins/brave-search/"
            "scripts/doctor.py",
        )


def test_no_install_example_enables_without_explicit_permission() -> None:
    install_pattern = re.compile(
        r"plugins install[^\n]*\s--enable(?:\s|$)"
    )
    enable_pattern = re.compile(
        r"^\s*hermes(?: --profile [^\s]+)? plugins enable brave-search[^\n]*$",
        re.MULTILINE,
    )

    for path in DOC_PATHS:
        text = read(path)
        assert install_pattern.search(text) is None, path
        for command in enable_pattern.findall(text):
            assert "--allow-tool-override" in command, (path, command)


def test_manual_configuration_includes_permission_and_brave_backends() -> None:
    for path in (ROOT / "README.md", ROOT / "docs" / "installation.md"):
        text = read(path)
        assert "allow_tool_override: true" in text
        assert 'backend: "brave-pro"' in text
        assert 'search_backend: "brave-pro"' in text
        for block in re.findall(r"```yaml\n(.*?)```", text, re.DOTALL):
            if "- brave-search" in block:
                assert "allow_tool_override: true" in block, path

    config = read(ROOT / "examples" / "config.yaml")
    assert_in_order(
        config,
        "entries:",
        "brave-search:",
        "allow_tool_override: true",
        'backend: "brave-pro"',
        'search_backend: "brave-pro"',
    )


def test_after_install_does_not_claim_private_picker_patching() -> None:
    text = read(ROOT / "after-install.md")
    assert "Current Hermes owns provider picker visibility" in text
    assert re.search(r"\bpatch(?:ed|ing)?\b", text, re.IGNORECASE) is None


def run_installer(home: Path, *, profile: str | None = None) -> str:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["HERMES_HOME"] = str(home / ".hermes")
    if profile is not None:
        env["HERMES_PROFILE"] = profile

    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "install.sh")],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_symlink_installer_prints_default_permission_and_restart_flow(
    tmp_path: Path,
) -> None:
    output = run_installer(tmp_path)
    hermes_home = tmp_path / ".hermes"
    assert "hermes plugins enable brave-search --allow-tool-override" in output
    assert "hermes gateway restart" in output
    assert f"backends in {hermes_home / 'config.yaml'}" in output
    assert 'backend: "brave-pro"' in output


def test_symlink_installer_prints_profile_permission_and_restart_flow(
    tmp_path: Path,
) -> None:
    output = run_installer(tmp_path, profile="MyProfile")
    profile_home = tmp_path / ".hermes" / "profiles" / "myprofile"
    assert (
        "hermes --profile myprofile plugins enable "
        "brave-search --allow-tool-override" in output
    )
    assert "hermes --profile myprofile gateway restart" in output
    assert f"backends in {profile_home / 'config.yaml'}" in output
    assert f"HERMES_HOME={profile_home}" in output
    assert f"{profile_home / 'plugins/brave-search/scripts/doctor.py'}" in output


def test_symlink_installer_maps_default_profile_to_root(tmp_path: Path) -> None:
    output = run_installer(tmp_path, profile="default")

    assert str(tmp_path / ".hermes" / "plugins" / "brave-search") in output
    assert "profiles/default" not in output
    assert "hermes --profile default plugins enable" in output


def test_symlink_installer_rejects_unsafe_profile_names(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path),
            "HERMES_HOME": str(tmp_path / ".hermes"),
            "HERMES_PROFILE": "../escape",
        }
    )

    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "install.sh")],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Invalid Hermes profile name" in result.stderr
    assert not (tmp_path / "escape").exists()
