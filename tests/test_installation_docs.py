from __future__ import annotations

import os
import re
import shutil
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


def test_fresh_install_guidance_completes_backend_before_optional_desktop() -> None:
    for path in (ROOT / "README.md", ROOT / "docs" / "installation.md"):
        text = read(path)
        assert_in_order(
            text,
            "hermes plugins install GodsBoy/hermes-brave-search-pro --no-enable",
            "hermes plugins enable brave-search",
            "hermes gateway restart",
            "## Desktop Brave Search",
            "scripts/install-desktop.sh",
        )


def test_direct_and_profile_guidance_complete_backend_before_optional_desktop() -> None:
    for path in (ROOT / "README.md", ROOT / "docs" / "installation.md"):
        text = read(path)
        assert_in_order(
            text,
            "git clone https://github.com/GodsBoy/hermes-brave-search-pro.git \\\n"
            "  ~/.hermes/plugins/brave-search",
            "hermes plugins enable brave-search",
            "hermes gateway restart",
            "## Desktop Brave Search",
            "~/.hermes/plugins/brave-search/scripts/install-desktop.sh",
        )
        assert_in_order(
            text,
            "git clone https://github.com/GodsBoy/hermes-brave-search-pro.git \\\n"
            "  ~/.hermes/profiles/myprofile/plugins/brave-search",
            "hermes --profile myprofile plugins enable brave-search",
            "hermes --profile myprofile gateway restart",
            "python3 ~/.hermes/profiles/myprofile/plugins/brave-search/"
            "scripts/doctor.py",
            "## Desktop Brave Search",
            "HERMES_PROFILE=myprofile \\\n"
            "  ~/.hermes/profiles/myprofile/plugins/brave-search/"
            "scripts/install-desktop.sh",
        )


def test_install_examples_use_capability_consent_flow() -> None:
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
            assert "--allow-tool-override" not in command, (path, command)

    combined = "\n".join(read(path) for path in DOC_PATHS)
    assert "tools.override" in combined
    assert "granted_capabilities" in combined
    assert "capabilities_consent" in combined
    assert "allow_tool_override" in combined
    assert "legacy" in combined.lower()


def test_manual_configuration_uses_consent_and_brave_backends() -> None:
    for path in (ROOT / "README.md", ROOT / "docs" / "installation.md"):
        text = read(path)
        assert "hermes plugins enable brave-search" in text
        assert "granted_capabilities" in text
        assert "capabilities_consent" in text
        assert "granted_capabilities:" not in text
        assert "capabilities_consent:" not in text
        assert 'search_backend: "brave-pro"' in text

    config = read(ROOT / "examples" / "config.yaml")
    assert_in_order(
        config,
        "hermes plugins enable brave-search",
        "granted_capabilities",
        "capabilities_consent",
        'search_backend: "brave-pro"',
    )
    assert "granted_capabilities:" not in config
    assert "capabilities_consent:" not in config
    enabled_block = re.search(
        r"(?m)^plugins:\n  enabled:\n(?P<items>(?:    - [^\n]+\n)+)",
        config,
    )
    assert enabled_block is not None
    enabled_plugins = set(
        re.findall(r"(?m)^    - ([a-z0-9-]+)\s*$", enabled_block.group("items"))
    )
    assert enabled_plugins == {"brave-search"}
    assert 'extract_backend: "tavily"' in config


def test_tavily_is_owned_by_hermes_and_remains_optional() -> None:
    for path in (
        ROOT / "README.md",
        ROOT / "docs" / "installation.md",
        ROOT / "after-install.md",
        ROOT / "examples" / "config.yaml",
    ):
        text = read(path)
        assert "web-tavily" in text, path
        assert "bundled" in text.lower(), path
        assert "TAVILY_API_KEY" in text, path
        assert "optional" in text.lower(), path
        assert "brave-search" in text, path


def test_after_install_does_not_claim_private_picker_patching() -> None:
    text = read(ROOT / "after-install.md")
    assert "Current Hermes owns provider picker visibility" in text
    assert re.search(r"\bpatch(?:ed|ing)?\b", text, re.IGNORECASE) is None


def test_after_install_includes_matching_default_and_named_profile_flows() -> None:
    text = read(ROOT / "after-install.md")
    assert_in_order(
        text,
        "### Default profile",
        "hermes plugins enable brave-search",
        "hermes gateway restart",
        "## Desktop Brave Search",
        "~/.hermes/plugins/brave-search/scripts/install-desktop.sh",
    )
    assert_in_order(
        text,
        "### Named profile",
        "hermes --profile myprofile plugins enable ",
        "brave-search",
        "hermes --profile myprofile gateway restart",
        "## Desktop Brave Search",
        "~/.hermes/profiles/myprofile/plugins/brave-search/scripts/install-desktop.sh",
    )


def test_desktop_guidance_keeps_renderer_and_backend_boundaries_explicit() -> None:
    for path in (
        ROOT / "README.md",
        ROOT / "docs" / "installation.md",
        ROOT / "after-install.md",
    ):
        text = read(path)
        assert "desktop-plugins/brave-search" in text
        assert "Settings" in text
        assert "separate" in text.lower()
        assert "active profile" in text.lower()
        assert "remote" in text.lower()
        assert "leaves `plugins/brave-search` untouched" in text
        assert "does not require a gateway restart" in " ".join(text.lower().split())
        assert "does not automatically import" in " ".join(text.lower().split())


def test_remote_desktop_guidance_uses_a_persistent_local_renderer_checkout() -> None:
    for path in (
        ROOT / "README.md",
        ROOT / "docs" / "installation.md",
        ROOT / "after-install.md",
    ):
        text = read(path)
        assert_in_order(
            text,
            "Remote backend",
            "git clone https://github.com/GodsBoy/hermes-brave-search-pro.git \\\n"
            "  ~/hermes-brave-search-desktop",
            "~/hermes-brave-search-desktop/scripts/install-desktop.sh",
            "HERMES_PROFILE=myprofile \\\n"
            "  ~/hermes-brave-search-desktop/scripts/install-desktop.sh",
            "Keep this checkout",
        )
        assert "does not create a local backend link" in text


def test_desktop_guidance_requires_only_brave_and_keeps_tavily_optional() -> None:
    for path in (ROOT / "README.md", ROOT / "docs" / "installation.md"):
        text = read(path)
        desktop_section = text[text.index("## Desktop Brave Search") :]
        assert "BRAVE_SEARCH_API_KEY" in desktop_section
        assert "TAVILY_API_KEY" not in desktop_section
        assert "optional" in desktop_section.lower()


def test_static_doctor_guidance_uses_python3_with_installer_fallback() -> None:
    for path in (
        ROOT / "README.md",
        ROOT / "docs" / "installation.md",
        ROOT / "after-install.md",
    ):
        doctor_commands = re.findall(
            r"^([^\s]+) [^\n]*scripts/doctor\.py(?: [^\n]*)?$",
            read(path),
            re.MULTILINE,
        )
        assert doctor_commands, path
        assert set(doctor_commands) == {"python3"}, path
        assert (
            "exact interpreter printed by `./scripts/install.sh`"
            in " ".join(read(path).split())
        )


def run_installer(home: Path, *, profile: str | None = None) -> str:
    return run_script(home, "install.sh", profile=profile)


def run_script(
    home: Path,
    script_name: str,
    *,
    profile: str | None = None,
    check: bool = True,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str] | str:
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["HERMES_HOME"] = str(home / ".hermes")
    if profile is not None:
        env["HERMES_PROFILE"] = profile
    if extra_env is not None:
        env.update(extra_env)

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


def write_fake_python(
    path: Path,
    *,
    real_python: str,
    version: tuple[int, int],
) -> None:
    path.write_text(
        f"#!{real_python}\n"
        "import os\n"
        "import sys\n"
        'if sys.argv[1:2] == ["-c"]:\n'
        f"    raise SystemExit(not ((3, 11) <= {version!r} < (3, 14)))\n"
        f"os.execv({real_python!r}, [{real_python!r}, *sys.argv[1:]])\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_symlink_installer_prints_default_permission_and_restart_flow(
    tmp_path: Path,
) -> None:
    output = run_installer(tmp_path)
    hermes_home = tmp_path / ".hermes"
    assert "hermes plugins enable brave-search" in output
    assert "--allow-tool-override" not in output
    assert "tools.override" in output
    assert "hermes gateway restart" in output
    assert f"search backend in {hermes_home / 'config.yaml'}" in output
    assert 'search_backend: "brave-pro"' in output
    assert "TAVILY_API_KEY" in output
    assert "Tavily extraction is optional" in output
    assert "web-tavily" in output


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
    assert "hermes --profile myprofile plugins enable brave-search" in output
    assert "--allow-tool-override" not in output
    assert "hermes --profile myprofile gateway restart" in output
    assert f"search backend in {profile_home / 'config.yaml'}" in output
    assert f"HERMES_HOME={profile_home}" in output
    assert f"{profile_home / 'plugins/brave-search/scripts/doctor.py'}" in output


def test_symlink_installer_prints_selected_python_for_doctor(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python_binary = shutil.which("python3") or shutil.which("python")
    assert python_binary is not None
    selected_python = bin_dir / "python3"
    write_fake_python(
        selected_python,
        real_python=python_binary,
        version=(3, 13),
    )

    output = run_script(
        tmp_path,
        "install.sh",
        extra_env={"PATH": f"{bin_dir}:{os.environ['PATH']}"},
    )

    assert isinstance(output, str)
    doctor_path = tmp_path / ".hermes/plugins/brave-search/scripts/doctor.py"
    expected_doctor_command = (
        f"HERMES_HOME={tmp_path / '.hermes'} {selected_python} {doctor_path}"
    )
    assert expected_doctor_command in output


def test_symlink_installer_falls_back_to_python_when_python3_is_unsupported(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python_binary = shutil.which("python3") or shutil.which("python")
    assert python_binary is not None

    rejected_python3 = bin_dir / "python3"
    selected_python = bin_dir / "python"
    write_fake_python(
        rejected_python3,
        real_python=python_binary,
        version=(3, 10),
    )
    write_fake_python(
        selected_python,
        real_python=python_binary,
        version=(3, 13),
    )

    output = run_script(
        tmp_path,
        "install.sh",
        extra_env={"PATH": f"{bin_dir}:{os.environ['PATH']}"},
    )

    assert isinstance(output, str)
    doctor_path = tmp_path / ".hermes/plugins/brave-search/scripts/doctor.py"
    expected_doctor_command = (
        f"HERMES_HOME={tmp_path / '.hermes'} {selected_python} {doctor_path}"
    )
    assert expected_doctor_command in output
    assert str(rejected_python3) not in output


def test_symlink_installer_rejects_unsupported_python_versions(
    tmp_path: Path,
) -> None:
    python_binary = shutil.which("python3") or shutil.which("python")
    assert python_binary is not None

    for version in ((3, 10), (3, 14)):
        case_home = tmp_path / ".".join(map(str, version))
        bin_dir = case_home / "bin"
        bin_dir.mkdir(parents=True)

        for candidate in ("python3", "python"):
            write_fake_python(
                bin_dir / candidate,
                real_python=python_binary,
                version=version,
            )

        result = run_script(
            case_home,
            "install.sh",
            check=False,
            extra_env={"PATH": f"{bin_dir}:{os.environ['PATH']}"},
        )

        assert isinstance(result, subprocess.CompletedProcess)
        assert result.returncode == 1
        assert "Python 3.11 through 3.13 is required" in result.stderr
        assert not (case_home / ".hermes/plugins/brave-search").exists()


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


def test_symlink_installer_refuses_post_preflight_conflict(
    tmp_path: Path,
) -> None:
    hermes_home = tmp_path / ".hermes"
    backend_target = hermes_home / "plugins" / "brave-search"
    desktop_target = hermes_home / "desktop-plugins" / "brave-search"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    mkdir_binary = shutil.which("mkdir")
    assert mkdir_binary is not None
    (bin_dir / "mkdir").write_text(
        "#!/bin/sh\n"
        f'"{mkdir_binary}" -p "$INSTALL_TEST_RACE_PARENT"\n'
        'printf "conflict" > "$INSTALL_TEST_RACE_TARGET"\n'
        f'exec "{mkdir_binary}" "$@"\n',
        encoding="utf-8",
    )
    (bin_dir / "mkdir").chmod(0o755)

    result = run_script(
        tmp_path,
        "install.sh",
        check=False,
        extra_env={
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "INSTALL_TEST_RACE_PARENT": str(backend_target.parent),
            "INSTALL_TEST_RACE_TARGET": str(backend_target),
        },
    )

    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 1
    assert "Refusing to overwrite existing plugin path" in result.stderr
    assert backend_target.read_text(encoding="utf-8") == "conflict"
    assert not desktop_target.exists()


def test_symlink_installer_rolls_back_only_its_first_link_on_second_link_failure(
    tmp_path: Path,
) -> None:
    hermes_home = tmp_path / ".hermes"
    backend_target = hermes_home / "plugins" / "brave-search"
    desktop_target = hermes_home / "desktop-plugins" / "brave-search"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python_binary = shutil.which("python3") or shutil.which("python")
    mkdir_binary = shutil.which("mkdir")
    assert python_binary is not None
    assert mkdir_binary is not None
    (bin_dir / "python3").write_text(
        "#!/bin/sh\n"
        'if [ "$3" = "$INSTALL_TEST_RACE_TARGET" ]; then\n'
        f'  "{mkdir_binary}" -p "$INSTALL_TEST_RACE_TARGET"\n'
        "  exit 1\n"
        "fi\n"
        f'exec "{python_binary}" "$@"\n',
        encoding="utf-8",
    )
    (bin_dir / "python3").chmod(0o755)

    result = run_script(
        tmp_path,
        "install.sh",
        check=False,
        extra_env={
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "INSTALL_TEST_RACE_TARGET": str(desktop_target),
        },
    )

    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 1
    assert "Refusing to overwrite existing plugin path" in result.stderr
    assert "Rolled back:" in result.stdout
    assert not backend_target.exists()
    assert desktop_target.is_dir()


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
