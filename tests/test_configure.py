from __future__ import annotations

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
        return CompatReport(config_changed=["web.backend"])

    monkeypatch.setattr("hermes_brave_search.configure.apply_runtime_compat", apply)

    assert main(["--force"]) == 0
    assert calls == [True]
    assert "Updated Hermes config: web.backend" in capsys.readouterr().out
