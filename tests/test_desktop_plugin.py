from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "desktop" / "plugin.js"


def plugin_source() -> str:
    return PLUGIN.read_text()


def test_desktop_plugin_is_plain_esm_with_only_supported_imports():
    source = plugin_source()

    imports = re.findall(
        r"^import(?:[\s\S]*?from\s+)?['\"]([^'\"]+)['\"]",
        source,
        re.MULTILINE,
    )

    assert set(imports) <= {"@hermes/plugin-sdk", "react", "react/jsx-runtime"}
    assert "<div" not in source
    subprocess.run(["node", "--check", str(PLUGIN)], check=True)


def test_desktop_plugin_registers_opt_in_brave_search_navigation_contract():
    source = plugin_source()

    assert "id: ID" in source
    assert "const ID = 'brave-search'" in source
    assert "defaultEnabled: false" in source
    assert "ROUTES_AREA" in source
    assert "SIDEBAR_NAV_AREA" in source
    assert "PALETTE_AREA" in source
    assert "const ROUTE = '/brave-search'" in source
    assert source.count("ROUTE") >= 4
    assert "host.navigate(ROUTE)" in source


def test_desktop_plugin_uses_only_scoped_search_requests_and_bounds_queries():
    source = plugin_source()

    assert "ctx.rest('/search'" in source
    assert "method: 'POST'" in source
    assert "body: { query }" in source
    assert "fetch(" not in source
    assert "process.env" not in source
    assert "BRAVE_API_KEY" not in source
    assert "MAX_QUERY_CHARACTERS = 400" in source
    assert "MAX_QUERY_WORDS = 50" in source
    assert ".trim()" in source
    assert "query.split(/\\s+/).length" in source


def test_desktop_plugin_has_accessible_validation_and_async_status_contract():
    source = plugin_source()

    assert "aria-describedby" in source
    assert "aria-invalid" in source
    assert "onBlur" in source
    assert "onSubmit" in source
    assert "focusQuery()" in source
    assert "document.getElementById('brave-search-query')?.focus()" in source
    assert "role: 'status'" in source
    assert "'aria-live': 'polite'" in source
    assert "kind: 'idle'" in source
    assert "kind: 'empty'" in source
    assert "kind: 'loading'" in source
    assert "kind: 'missing_credential'" in source
    assert "kind: 'backend_unavailable'" in source
    assert "kind: 'api_error'" in source


def test_desktop_plugin_rejects_stale_results_and_unsafe_external_urls():
    source = plugin_source()

    assert "generationRef.current" in source
    assert "if (generation !== generationRef.current)" in source
    assert "new URL(value.trim())" in source
    assert "url.protocol !== 'http:' && url.protocol !== 'https:'" in source
    assert "url.hostname" in source
    assert "window.hermesDesktop?.openExternal?.(url)" in source
    assert "window.open(" not in source
