from __future__ import annotations

import sys
import types

from hermes_brave_search.compat import (
    BRAVE_PRO_BACKEND,
    ensure_recommended_web_config,
    patch_tools_config_picker,
)


def test_patch_tools_config_picker_prefers_explicit_config(monkeypatch):
    tools_config = types.ModuleType("hermes_cli.tools_config")

    def is_provider_active(provider, config, *, force_fresh=False):
        return provider.get("web_backend") == config.get("web", {}).get(
            "search_backend"
        )

    def old_detect(providers, config, *, force_fresh=False):
        return 0

    tools_config._is_provider_active = is_provider_active  # type: ignore[attr-defined]
    tools_config._detect_active_provider_index = old_detect  # type: ignore[attr-defined]
    tools_config.get_env_value = lambda key: "present"  # type: ignore[attr-defined]

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.tools_config = tools_config  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.tools_config", tools_config)

    assert patch_tools_config_picker() is True

    providers = [
        {
            "name": "Brave Search (Free)",
            "web_backend": "brave-free",
            "env_vars": [{"key": "BRAVE_SEARCH_API_KEY"}],
        },
        {
            "name": "Brave Search Pro",
            "web_backend": BRAVE_PRO_BACKEND,
            "env_vars": [{"key": "BRAVE_SEARCH_API_KEY"}],
        },
    ]

    assert tools_config._detect_active_provider_index(
        providers,
        {"web": {"search_backend": BRAVE_PRO_BACKEND}},
    ) == 1


def test_patch_tools_config_picker_prefers_brave_pro_env_fallback(monkeypatch):
    tools_config = types.ModuleType("hermes_cli.tools_config")
    tools_config._is_provider_active = (  # type: ignore[attr-defined]
        lambda provider, config, *, force_fresh=False: False
    )
    tools_config._detect_active_provider_index = (  # type: ignore[attr-defined]
        lambda providers, config, *, force_fresh=False: 0
    )
    tools_config.get_env_value = (  # type: ignore[attr-defined]
        lambda key: "present" if key == "BRAVE_SEARCH_API_KEY" else ""
    )

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.tools_config = tools_config  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.tools_config", tools_config)

    patch_tools_config_picker()

    providers = [
        {
            "name": "Brave Search (Free)",
            "web_backend": "brave-free",
            "env_vars": [{"key": "BRAVE_SEARCH_API_KEY"}],
        },
        {
            "name": "Brave Search Pro",
            "web_backend": BRAVE_PRO_BACKEND,
            "env_vars": [{"key": "BRAVE_SEARCH_API_KEY"}],
        },
    ]

    assert tools_config._detect_active_provider_index(providers, {}) == 1


def test_ensure_recommended_web_config_sets_safe_defaults(monkeypatch):
    saved = {}
    config = {"web": {"backend": "brave-free", "search_backend": "brave-free"}}

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

    assert changed == ["web.backend", "web.search_backend", "web.extract_backend"]
    assert saved["web"] == {
        "backend": "brave-pro",
        "search_backend": "brave-pro",
        "extract_backend": "tavily",
    }


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
