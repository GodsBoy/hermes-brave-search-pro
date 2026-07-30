from __future__ import annotations

import sys
import types

from hermes_brave_search.doctor import main, run_checks


def _configured_plugins() -> dict:
    return {
        "enabled": ["brave-search", "web-tavily"],
        "entries": {
            "brave-search": {"allow_tool_override": True},
        },
    }


def test_doctor_checks_keys_plugins_permission_and_web_config(monkeypatch):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: {"brave-search": True, "web-tavily": True},
    )
    config = {
        "plugins": _configured_plugins(),
        "web": {
            "backend": "brave-pro",
            "search_backend": "brave-pro",
            "extract_backend": "tavily",
        },
    }

    config_mod = types.ModuleType("hermes_cli.config")
    config_mod.get_env_value = lambda key: "present"  # type: ignore[attr-defined]
    config_mod.load_config = lambda: config  # type: ignore[attr-defined]

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.config = config_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_mod)

    checks = run_checks()

    assert [check.name for check in checks] == [
        "BRAVE_SEARCH_API_KEY or BRAVE_API_KEY",
        "brave-search plugin",
        "brave-search tool override",
        "TAVILY_API_KEY",
        "web-tavily plugin",
        "web.backend",
        "web.search_backend",
        "web.extract_backend",
    ]
    assert all(check.ok for check in checks)


def test_doctor_fails_when_override_permission_is_missing(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: {"brave-search": True, "web-tavily": True},
    )
    config = {
        "plugins": {"enabled": ["brave-search", "web-tavily"]},
        "web": {
            "backend": "brave-pro",
            "search_backend": "brave-pro",
            "extract_backend": "tavily",
        },
    }

    config_mod = types.ModuleType("hermes_cli.config")
    config_mod.get_env_value = lambda key: "present"  # type: ignore[attr-defined]
    config_mod.load_config = lambda: config  # type: ignore[attr-defined]
    config_mod.save_config = lambda value: None  # type: ignore[attr-defined]

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.config = config_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_mod)

    assert main([]) == 1
    output = capsys.readouterr().out
    assert "brave-search tool override: missing" in output
    assert "plugins enable brave-search --allow-tool-override" in output


def test_doctor_reports_missing_tavily(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: {"brave-search": True, "web-tavily": False},
    )
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    config = {
        "plugins": _configured_plugins(),
        "web": {"backend": "brave-pro", "search_backend": "brave-pro"},
    }

    config_mod = types.ModuleType("hermes_cli.config")
    config_mod.get_env_value = (  # type: ignore[attr-defined]
        lambda key: "present" if key == "BRAVE_SEARCH_API_KEY" else ""
    )
    config_mod.load_config = lambda: config  # type: ignore[attr-defined]
    config_mod.save_config = lambda value: None  # type: ignore[attr-defined]

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.config = config_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_mod)

    assert main([]) == 1
    output = capsys.readouterr().out
    assert "TAVILY_API_KEY" in output
    assert "web-tavily plugin" in output
    assert "hermes plugins enable web-tavily" in output
    assert "missing" in output
    assert "--fix" in output


def test_doctor_without_fix_does_not_update_config(monkeypatch, capsys):
    def fail_if_called(**kwargs):
        raise AssertionError("plain doctor must not update config")

    monkeypatch.setattr(
        "hermes_brave_search.doctor.apply_runtime_compat",
        fail_if_called,
    )
    monkeypatch.setattr("hermes_brave_search.doctor.run_checks", lambda: [])

    assert main([]) == 0
    assert "All Brave Search Pro checks passed." in capsys.readouterr().out


def test_doctor_fix_reports_config_errors_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.compat.ensure_recommended_web_config",
        lambda **kwargs: (_ for _ in ()).throw(PermissionError("read-only config")),
        raising=False,
    )

    config_mod = types.ModuleType("hermes_cli.config")
    config_mod.get_env_value = lambda key: "present"  # type: ignore[attr-defined]
    config_mod.load_config = lambda: {}  # type: ignore[attr-defined]

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.config = config_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_mod)
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: None,
    )

    assert main(["--fix"]) == 1
    assert "Warning:" in capsys.readouterr().out
