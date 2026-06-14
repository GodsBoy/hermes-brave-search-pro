from __future__ import annotations

import sys
import types

from hermes_brave_search.doctor import main, run_checks


def test_doctor_checks_keys_and_web_config(monkeypatch):
    config = {
        "web": {
            "backend": "brave-pro",
            "search_backend": "brave-pro",
            "extract_backend": "tavily",
        }
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
        "TAVILY_API_KEY",
        "web.backend",
        "web.search_backend",
        "web.extract_backend",
    ]
    assert all(check.ok for check in checks)


def test_doctor_reports_missing_tavily(monkeypatch, capsys):
    config = {"web": {"backend": "brave-pro", "search_backend": "brave-pro"}}

    config_mod = types.ModuleType("hermes_cli.config")
    config_mod.get_env_value = (  # type: ignore[attr-defined]
        lambda key: "present" if key == "BRAVE_SEARCH_API_KEY" else ""
    )
    config_mod.load_config = lambda: config  # type: ignore[attr-defined]
    config_mod.save_config = lambda value: None  # type: ignore[attr-defined]

    tools_config = types.ModuleType("hermes_cli.tools_config")
    tools_config._detect_active_provider_index = (  # type: ignore[attr-defined]
        lambda providers, config, *, force_fresh=False: 0
    )

    hermes_cli = types.ModuleType("hermes_cli")
    hermes_cli.config = config_mod  # type: ignore[attr-defined]
    hermes_cli.tools_config = tools_config  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_cli", hermes_cli)
    monkeypatch.setitem(sys.modules, "hermes_cli.config", config_mod)
    monkeypatch.setitem(sys.modules, "hermes_cli.tools_config", tools_config)

    assert main([]) == 1
    output = capsys.readouterr().out
    assert "TAVILY_API_KEY" in output
    assert "missing" in output
    assert "--fix" in output
