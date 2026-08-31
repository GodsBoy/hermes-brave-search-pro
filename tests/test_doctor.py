from __future__ import annotations

import sys
import types

from hermes_brave_search.doctor import (
    Check,
    _tavily_provider_status,
    main,
    run_checks,
)


def _configured_plugins() -> dict:
    return {
        "enabled": ["brave-search"],
        "entries": {
            "brave-search": {"allow_tool_override": True},
        },
    }


def _present_env_value(_key: str) -> str:
    return "present"


def _install_config(
    monkeypatch,
    config: dict,
    *,
    get_env_value=_present_env_value,
) -> None:
    config_mod = types.ModuleType("hermes_cli.config")
    config_mod.get_env_value = get_env_value  # type: ignore[attr-defined]
    config_mod.load_config = lambda: config  # type: ignore[attr-defined]

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.config = config_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_mod)


def _install_web_registry(monkeypatch, provider, *, loader=None):
    registry_mod = types.ModuleType("agent.web_search_registry")
    registry_mod.get_provider = lambda name: (
        provider if name == "tavily" else None
    )  # type: ignore[attr-defined]
    web_tools_mod = types.ModuleType("tools.web_tools")
    web_tools_mod._ensure_web_plugins_loaded = loader or (  # type: ignore[attr-defined]
        lambda: None
    )
    monkeypatch.setitem(sys.modules, "agent.web_search_registry", registry_mod)
    monkeypatch.setitem(sys.modules, "tools.web_tools", web_tools_mod)


def test_tavily_provider_status_uses_registry_loader_and_capability(monkeypatch):
    calls = []
    provider = types.SimpleNamespace(
        supports_extract=lambda: calls.append("capability") or True,
    )
    _install_web_registry(
        monkeypatch,
        provider,
        loader=lambda: calls.append("loader"),
    )

    assert _tavily_provider_status() is True
    assert calls == ["loader", "capability"]


def test_tavily_provider_status_reports_unsupported_provider(monkeypatch):
    provider = types.SimpleNamespace(supports_extract=lambda: False)
    _install_web_registry(monkeypatch, provider)

    assert _tavily_provider_status() is False


def test_tavily_provider_status_returns_unknown_on_discovery_failure(monkeypatch):
    _install_web_registry(
        monkeypatch,
        types.SimpleNamespace(supports_extract=lambda: True),
        loader=lambda: (_ for _ in ()).throw(RuntimeError("discovery failed")),
    )

    assert _tavily_provider_status() is None


def test_doctor_checks_keys_plugins_permission_and_web_config(monkeypatch):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        # A stale legacy plugin-list entry must not determine Tavily readiness.
        lambda: {"brave-search": True, "web-tavily": False},
    )
    monkeypatch.setattr(
        "hermes_brave_search.doctor._tavily_provider_status",
        lambda: True,
    )
    config = {
        "plugins": _configured_plugins(),
        "web": {
            "backend": "brave-pro",
            "search_backend": "brave-pro",
            "extract_backend": "tavily",
        },
    }

    _install_config(monkeypatch, config)

    checks = run_checks()

    assert [check.name for check in checks] == [
        "BRAVE_SEARCH_API_KEY or BRAVE_API_KEY",
        "brave-search plugin",
        "brave-search tool override",
        "TAVILY_API_KEY",
        "tavily provider",
        "web.backend",
        "web.search_backend",
        "web.extract_backend",
    ]
    assert all(check.ok for check in checks)


def test_doctor_fails_when_override_permission_is_missing(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: {"brave-search": True},
    )
    monkeypatch.setattr(
        "hermes_brave_search.doctor._tavily_provider_status",
        lambda: True,
    )
    config = {
        "plugins": {"enabled": ["brave-search"]},
        "web": {
            "backend": "brave-pro",
            "search_backend": "brave-pro",
            "extract_backend": "tavily",
        },
    }

    _install_config(monkeypatch, config)

    assert main([]) == 1
    output = capsys.readouterr().out
    assert "brave-search tool override: missing" in output
    assert "plugins enable brave-search --allow-tool-override" in output


def test_doctor_reports_missing_tavily(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: {"brave-search": True},
    )
    monkeypatch.setattr(
        "hermes_brave_search.doctor._tavily_provider_status",
        lambda: False,
    )
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    config = {
        "plugins": _configured_plugins(),
        "web": {"backend": "brave-pro", "search_backend": "brave-pro"},
    }

    _install_config(
        monkeypatch,
        config,
        get_env_value=lambda key: (
            "present" if key == "BRAVE_SEARCH_API_KEY" else ""
        ),
    )

    assert main([]) == 0
    output = capsys.readouterr().out
    assert "TAVILY_API_KEY" in output
    assert "tavily provider" in output
    assert "hermes tools" in output
    assert "missing" in output
    assert "[advisory]" in output


def test_doctor_explicit_tavily_missing_key_is_fatal(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: {"brave-search": True},
    )
    monkeypatch.setattr(
        "hermes_brave_search.doctor._tavily_provider_status",
        lambda: True,
    )
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    config = {
        "plugins": _configured_plugins(),
        "web": {
            "backend": "brave-pro",
            "search_backend": "brave-pro",
            "extract_backend": "tavily",
        },
    }

    _install_config(
        monkeypatch,
        config,
        get_env_value=lambda key: (
            "present" if key == "BRAVE_SEARCH_API_KEY" else ""
        ),
    )

    assert main([]) == 1
    output = capsys.readouterr().out
    assert "TAVILY_API_KEY" in output
    assert "advisory" not in output


def test_doctor_explicit_tavily_unsupported_provider_is_fatal(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: {"brave-search": True},
    )
    monkeypatch.setattr(
        "hermes_brave_search.doctor._tavily_provider_status",
        lambda: False,
    )
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key")
    config = {
        "plugins": _configured_plugins(),
        "web": {
            "backend": "brave-pro",
            "search_backend": "brave-pro",
            "extract_backend": "tavily",
        },
    }
    _install_config(monkeypatch, config)

    assert main([]) == 1
    output = capsys.readouterr().out
    assert "tavily provider: not registered" in output


def test_doctor_non_tavily_extract_provider_keeps_tavily_advisory(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: {"brave-search": True},
    )
    monkeypatch.setattr(
        "hermes_brave_search.doctor._tavily_provider_status",
        lambda: False,
    )
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    config = {
        "plugins": _configured_plugins(),
        "web": {
            "backend": "brave-pro",
            "search_backend": "brave-pro",
            "extract_backend": "builtin",
        },
    }
    _install_config(
        monkeypatch,
        config,
        get_env_value=lambda key: (
            "present" if key == "BRAVE_SEARCH_API_KEY" else ""
        ),
    )

    assert main([]) == 0
    output = capsys.readouterr().out
    assert "TAVILY_API_KEY: missing" in output
    assert "[advisory]" in output
    assert "All required Brave Search Pro checks passed." in output


def test_doctor_explicit_tavily_unknown_provider_is_fatal(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: None,
    )
    monkeypatch.setattr(
        "hermes_brave_search.doctor._tavily_provider_status",
        lambda: None,
    )
    config = {
        "plugins": _configured_plugins(),
        "web": {
            "backend": "brave-pro",
            "search_backend": "brave-pro",
            "extract_backend": "tavily",
        },
    }
    _install_config(monkeypatch, config)

    assert main([]) == 1
    output = capsys.readouterr().out
    assert "tavily provider: unable to verify" in output
    assert "[advisory]" not in output


def test_doctor_missing_brave_override_is_fatal_when_tavily_unselected(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: {"brave-search": True},
    )
    monkeypatch.setattr(
        "hermes_brave_search.doctor._tavily_provider_status",
        lambda: False,
    )
    config = {
        "plugins": {"enabled": ["brave-search"]},
        "web": {
            "backend": "brave-pro",
            "search_backend": "brave-pro",
            "extract_backend": "builtin",
        },
    }
    _install_config(
        monkeypatch,
        config,
        get_env_value=lambda key: (
            "present" if key == "BRAVE_SEARCH_API_KEY" else ""
        ),
    )

    assert main([]) == 1
    output = capsys.readouterr().out
    assert "brave-search tool override: missing" in output
    assert "TAVILY_API_KEY" in output
    assert "[advisory]" in output


def test_doctor_full_tavily_configuration_passes_main(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: {"brave-search": True},
    )
    monkeypatch.setattr(
        "hermes_brave_search.doctor._tavily_provider_status",
        lambda: True,
    )
    config = {
        "plugins": _configured_plugins(),
        "web": {
            "backend": "brave-pro",
            "search_backend": "brave-pro",
            "extract_backend": "tavily",
        },
    }
    _install_config(monkeypatch, config)

    assert main([]) == 0
    output = capsys.readouterr().out
    assert "All required Brave Search Pro checks passed." in output
    assert "[advisory]" not in output


def test_doctor_nonblocking_failed_check_is_advisory(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.doctor.run_checks",
        lambda: [Check("optional", False, "missing", blocking=False)],
    )

    assert main([]) == 0
    output = capsys.readouterr().out
    assert "! optional: missing [advisory]" in output
    assert "All required Brave Search Pro checks passed." in output


def test_doctor_failed_three_argument_check_is_blocking(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.doctor.run_checks",
        lambda: [Check("required", False, "missing")],
    )

    assert main([]) == 1
    assert "required: missing" in capsys.readouterr().out


def test_doctor_without_fix_does_not_update_config(monkeypatch, capsys):
    def fail_if_called(**kwargs):
        raise AssertionError("plain doctor must not update config")

    monkeypatch.setattr(
        "hermes_brave_search.doctor.apply_runtime_compat",
        fail_if_called,
    )
    monkeypatch.setattr("hermes_brave_search.doctor.run_checks", lambda: [])

    assert main([]) == 0
    assert "All required Brave Search Pro checks passed." in capsys.readouterr().out


def test_doctor_passes_with_non_empty_successful_checks(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.doctor.run_checks",
        lambda: [Check("configured", True, "present")],
    )

    assert main([]) == 0
    output = capsys.readouterr().out
    assert "✓ configured: present" in output
    assert "All required Brave Search Pro checks passed." in output


def test_doctor_fix_reports_config_errors_without_traceback(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.compat.ensure_recommended_web_config",
        lambda **kwargs: (_ for _ in ()).throw(PermissionError("read-only config")),
        raising=False,
    )

    _install_config(monkeypatch, {})
    monkeypatch.setattr(
        "hermes_brave_search.doctor._plugin_statuses",
        lambda: None,
    )

    assert main(["--fix"]) == 1
    assert "Warning:" in capsys.readouterr().out
