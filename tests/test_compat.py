from __future__ import annotations

import sys
import types

from hermes_brave_search.compat import (
    CompatReport,
    _get_env_value,
    apply_runtime_compat,
    ensure_recommended_web_config,
)


def test_ensure_recommended_web_config_sets_safe_defaults(monkeypatch):
    saved = {}
    config = {
        "web": {
            "backend": "brave-free",
            "search_backend": "brave-free",
            "extract_backend": "firecrawl",
        }
    }

    config_mod = types.ModuleType("hermes_cli.config")
    config_mod.get_env_value = lambda key: "present"  # type: ignore[attr-defined]
    config_mod.load_config = lambda: config  # type: ignore[attr-defined]
    config_mod.save_config = (  # type: ignore[attr-defined]
        lambda value: saved.update(value)
    )

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.config = config_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_mod)

    changed = ensure_recommended_web_config()

    assert changed == ["web.search_backend"]
    assert saved["web"] == {
        "backend": "brave-free",
        "search_backend": "brave-pro",
        "extract_backend": "firecrawl",
    }


def test_ensure_recommended_web_config_keeps_shared_backend_unset_without_extraction(
    monkeypatch,
):
    saved = {}
    config = {"web": {"search_backend": ""}}

    config_mod = types.ModuleType("hermes_cli.config")
    config_mod.get_env_value = (  # type: ignore[attr-defined]
        lambda key: {
            "BRAVE_SEARCH_API_KEY": "brave-key",
            "TAVILY_API_KEY": "tavily-key",
        }.get(key)
    )
    config_mod.load_config = lambda: config  # type: ignore[attr-defined]
    config_mod.save_config = lambda value: saved.update(value)  # type: ignore[attr-defined]

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.config = config_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_mod)

    assert ensure_recommended_web_config(force=True) == [
        "web.search_backend",
    ]
    assert saved["web"] == {"search_backend": "brave-pro"}


def test_ensure_recommended_web_config_does_not_override_other_providers(monkeypatch):
    saved = {}
    config = {
        "web": {
            "backend": "exa",
            "search_backend": "exa",
            "extract_backend": "firecrawl",
        }
    }

    config_mod = types.ModuleType("hermes_cli.config")
    config_mod.get_env_value = lambda key: "present"  # type: ignore[attr-defined]
    config_mod.load_config = lambda: config  # type: ignore[attr-defined]
    config_mod.save_config = (  # type: ignore[attr-defined]
        lambda value: saved.update(value)
    )

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.config = config_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_mod)

    assert ensure_recommended_web_config() == []
    assert saved == {}
    assert config["web"] == {
        "backend": "exa",
        "search_backend": "exa",
        "extract_backend": "firecrawl",
    }


def test_compat_report_changed_tracks_config_updates():
    assert CompatReport().changed is False
    assert CompatReport(config_changed=["web.search_backend"]).changed is True


def test_get_env_value_does_not_borrow_process_key_after_scoped_miss(
    monkeypatch,
):
    config_mod = types.ModuleType("hermes_cli.config")
    config_mod.get_env_value = lambda key: None  # type: ignore[attr-defined]

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.config = config_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_mod)
    monkeypatch.setenv("TAVILY_API_KEY", "another-profile-key")

    assert _get_env_value("TAVILY_API_KEY") is None


def test_get_env_value_preserves_scope_isolation_errors(monkeypatch):
    config_mod = types.ModuleType("hermes_cli.config")

    def fail_closed(key):
        raise RuntimeError(f"unscoped secret: {key}")

    config_mod.get_env_value = fail_closed  # type: ignore[attr-defined]

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.config = config_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_mod)
    monkeypatch.setenv("TAVILY_API_KEY", "another-profile-key")

    try:
        _get_env_value("TAVILY_API_KEY")
    except RuntimeError as exc:
        assert str(exc) == "unscoped secret: TAVILY_API_KEY"
    else:  # pragma: no cover - assertion aid
        raise AssertionError("scope-isolation error was swallowed")


def test_apply_runtime_compat_captures_config_errors(monkeypatch):
    def fail_config_update(*, force=False):
        assert force is True
        raise RuntimeError("config unavailable")

    monkeypatch.setattr(
        "hermes_brave_search.compat.ensure_recommended_web_config",
        fail_config_update,
    )

    report = apply_runtime_compat(force=True)

    assert report.config_changed == []
    assert report.errors == ["config update failed: config unavailable"]
