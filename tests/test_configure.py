from __future__ import annotations

import pytest

from hermes_brave_search.compat import CompatReport
from hermes_brave_search.configure import main


def test_configure_reports_compatibility_errors(monkeypatch, capsys):
    monkeypatch.setattr(
        "hermes_brave_search.configure.apply_runtime_compat",
        lambda **kwargs: CompatReport(
            errors=["Hermes configuration API is unavailable"]
        ),
    )

    assert main([]) == 1
    assert "Error: Hermes configuration API is unavailable" in capsys.readouterr().out


def test_configure_forwards_force_and_reports_changes(monkeypatch, capsys):
    calls = []

    def apply(*, force=False):
        calls.append(force)
        return CompatReport(config_changed=["web.search_backend"])

    monkeypatch.setattr("hermes_brave_search.configure.apply_runtime_compat", apply)

    assert main(["--force"]) == 0
    assert calls == [True]
    assert "Updated Hermes config: web.search_backend" in capsys.readouterr().out


def test_configure_help_describes_routing_and_preserved_extraction(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    help_output = capsys.readouterr().out
    assert "Configure Hermes web search routing for Brave Search Pro" in help_output
    assert "Existing extraction settings are preserved" in help_output
    assert "select bundled Tavily explicitly when desired" in help_output
    assert "optional Tavily extraction config" not in help_output
