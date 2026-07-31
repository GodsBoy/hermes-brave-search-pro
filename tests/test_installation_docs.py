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
    ROOT / "scripts" / "install-desktop.sh",
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
            "scripts/install-desktop.sh",
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
            "~/.hermes/plugins/brave-search/scripts/install-desktop.sh",
            "hermes plugins enable brave-search --allow-tool-override",
            "hermes gateway restart",
        )
        assert_in_order(
            text,
            "git clone https://github.com/GodsBoy/hermes-brave-search-pro.git \\\n"
            "  ~/.hermes/profiles/myprofile/plugins/brave-search",
            "HERMES_PROFILE=myprofile \\\n"
            "  ~/.hermes/profiles/myprofile/plugins/brave-search/"
            "scripts/install-desktop.sh",
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


def test_desktop_guidance_keeps_renderer_and_backend_boundaries_explicit() -> None:
    for path in (ROOT / "README.md", ROOT / "docs" / "installation.md"):
        text = read(path)
        assert "desktop-plugins/brave-search" in text
        assert "Settings" in text
        assert "separate" in text.lower()
        assert "active profile" in text.lower()
        assert "remote" in text.lower()
        assert "does not automatically import" in text.lower()


def test_desktop_guidance_requires_only_brave_and_keeps_tavily_optional() -> None:
    for path in (ROOT / "README.md", ROOT / "docs" / "installation.md"):
        text = read(path)
        desktop_section = text[text.index("## Desktop Brave Search") :]
        assert "BRAVE_SEARCH_API_KEY" in desktop_section
        assert "TAVILY_API_KEY" not in desktop_section
        assert "optional" in desktop_section.lower()


def run_installer(home: Path, *, profile: str | None = None) -> str:
    return run_script(home, "install.sh", profile=profile)


def run_script(
    home: Path,
    script_name: str,
    *,
    profile: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str] | str:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["HERMES_HOME"] = str(home / ".hermes")
    if profile is not None:
        env["HERMES_PROFILE"] = profile

    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / script_name)],
        cwd=ROOT,
        env=env,
        check=check,
        capture_output=True,
        text=True,
    )
    if check:
        return result.stdout
    return result


def test_symlink_installer_prints_default_permission_and_restart_flow(
    tmp_path: Path,
) -> None:
    output = run_installer(tmp_path)
    hermes_home = tmp_path / ".hermes"
    assert "hermes plugins enable brave-search --allow-tool-override" in output
    assert "hermes gateway restart" in output
    assert f"backends in {hermes_home / 'config.yaml'}" in output
    assert 'backend: "brave-pro"' in output


def test_symlink_installer_links_both_surfaces_and_is_idempotent(
    tmp_path: Path,
) -> None:
    first_output = run_installer(tmp_path)
    hermes_home = tmp_path / ".hermes"
    backend_target = hermes_home / "plugins" / "brave-search"
    desktop_target = hermes_home / "desktop-plugins" / "brave-search"

    assert backend_target.is_symlink()
    assert backend_target.resolve() == ROOT
    assert desktop_target.is_symlink()
    assert desktop_target.resolve() == ROOT / "desktop"
    assert "Installed:" in first_output

    second_output = run_installer(tmp_path)
    assert f"Already installed: {backend_target} -> {ROOT}" in second_output
    assert f"Already installed: {desktop_target} -> {ROOT / 'desktop'}" in second_output


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


def test_symlink_installer_links_both_named_profile_surfaces(
    tmp_path: Path,
) -> None:
    run_installer(tmp_path, profile="MyProfile")
    profile_home = tmp_path / ".hermes" / "profiles" / "myprofile"

    assert (profile_home / "plugins" / "brave-search").resolve() == ROOT
    assert (profile_home / "desktop-plugins" / "brave-search").resolve() == (
        ROOT / "desktop"
    )


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


def test_symlink_installer_rejects_reserved_profile_before_linking(
    tmp_path: Path,
) -> None:
    result = run_script(
        tmp_path,
        "install.sh",
        profile="root",
        check=False,
    )

    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 1
    assert "Reserved Hermes profile name" in result.stderr
    assert not (tmp_path / ".hermes" / "plugins" / "brave-search").exists()
    assert not (
        tmp_path / ".hermes" / "desktop-plugins" / "brave-search"
    ).exists()


def test_symlink_installer_preflights_both_targets_before_linking(
    tmp_path: Path,
) -> None:
    for target_name in ("plugins", "desktop-plugins"):
        for conflict_kind in ("file", "directory", "symlink"):
            case_home = tmp_path / f"{target_name}-{conflict_kind}"
            hermes_home = case_home / ".hermes"
            backend_target = hermes_home / "plugins" / "brave-search"
            desktop_target = hermes_home / "desktop-plugins" / "brave-search"
            conflict_target = (
                backend_target if target_name == "plugins" else desktop_target
            )
            conflict_target.parent.mkdir(parents=True)

            unrelated = case_home / "unrelated"
            if conflict_kind == "file":
                conflict_target.write_text("keep me", encoding="utf-8")
            elif conflict_kind == "directory":
                conflict_target.mkdir()
            else:
                unrelated.mkdir()
                conflict_target.symlink_to(unrelated)

            result = run_script(case_home, "install.sh", check=False)

            assert isinstance(result, subprocess.CompletedProcess)
            assert result.returncode == 1
            assert "Refusing to overwrite existing plugin path" in result.stderr
            if conflict_kind == "file":
                assert conflict_target.read_text(encoding="utf-8") == "keep me"
            elif conflict_kind == "directory":
                assert conflict_target.is_dir()
            else:
                assert conflict_target.is_symlink()
                assert conflict_target.resolve() == unrelated

            other_target = (
                desktop_target
                if target_name == "plugins"
                else backend_target
            )
            assert not other_target.exists()


def test_standalone_desktop_installer_links_only_desktop_surface(
    tmp_path: Path,
) -> None:
    first_output = run_script(tmp_path, "install-desktop.sh")
    assert isinstance(first_output, str)
    hermes_home = tmp_path / ".hermes"
    desktop_target = hermes_home / "desktop-plugins" / "brave-search"

    assert desktop_target.is_symlink()
    assert desktop_target.resolve() == ROOT / "desktop"
    assert not (hermes_home / "plugins" / "brave-search").exists()
    assert "Settings" in first_output

    second_output = run_script(tmp_path, "install-desktop.sh")
    assert isinstance(second_output, str)
    assert f"Already installed: {desktop_target} -> {ROOT / 'desktop'}" in second_output


def test_standalone_desktop_installer_normalizes_profile_and_refuses_reserved(
    tmp_path: Path,
) -> None:
    output = run_script(tmp_path, "install-desktop.sh", profile="MyProfile")
    assert isinstance(output, str)
    profile_target = (
        tmp_path
        / ".hermes"
        / "profiles"
        / "myprofile"
        / "desktop-plugins"
        / "brave-search"
    )
    assert profile_target.resolve() == ROOT / "desktop"

    result = run_script(
        tmp_path / "reserved",
        "install-desktop.sh",
        profile="root",
        check=False,
    )
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 1
    assert "Reserved Hermes profile name" in result.stderr
