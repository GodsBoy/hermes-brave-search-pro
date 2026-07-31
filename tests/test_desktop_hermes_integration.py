from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "brave-search"


_SCENARIO = textwrap.dedent(
    """
    import json
    import sys
    from pathlib import Path

    enabled = sys.argv[1] == "enabled"

    assert "hermes_brave_search" not in sys.modules
    from fastapi.testclient import TestClient
    from hermes_cli import web_server

    mounted = any(
        route.path == "/api/plugins/brave-search/search"
        for route in web_server.app.routes
    )
    package = sys.modules.get("hermes_brave_search")

    result = {
        "mounted": mounted,
        "package_path": (
            str(Path(package.__file__).resolve().parent) if package else None
        ),
    }

    client = TestClient(web_server.app)
    unauthenticated = client.post(
        "/api/plugins/brave-search/search", json={"query": "Hermes Agent"}
    )
    result["unauthenticated_status"] = unauthenticated.status_code
    result["unauthenticated_body"] = unauthenticated.json()

    headers = {"X-Hermes-Session-Token": web_server._SESSION_TOKEN}
    if enabled:
        import hermes_brave_search.desktop as desktop

        class FakeClient:
            calls = []

            def __init__(self, *args, **kwargs):
                pass

            def resolved_api_key(self):
                return "configured"

            def search(self, query, *, mode, limit):
                self.calls.append({"query": query, "mode": mode, "limit": limit})
                return {
                    "success": True,
                    "data": {
                        "web": [
                            {
                                "title": "Hermes Agent",
                                "description": "Desktop plugin documentation",
                                "url": "https://hermes-agent.nousresearch.com/docs",
                                "position": 1,
                            }
                        ]
                    },
                }

        desktop.BraveSearchClient = FakeClient
        response = client.post(
            "/api/plugins/brave-search/search",
            json={"query": "Hermes Agent"},
            headers=headers,
        )
        result["authenticated_status"] = response.status_code
        result["authenticated_body"] = response.json()
        result["client_calls"] = FakeClient.calls
    else:
        response = client.post(
            "/api/plugins/brave-search/search",
            json={"query": "Hermes Agent"},
            headers=headers,
        )
        result["authenticated_status"] = response.status_code
        result["authenticated_body"] = response.json()

    print(json.dumps(result))
    """
)


_DESKTOP_LOADER_SMOKE = textwrap.dedent(
    """
    import { readFileSync } from 'node:fs'
    import { afterAll, beforeAll, expect, test } from 'vitest'

    import { PALETTE_AREA } from '@/app/command-palette/contrib'
    import { ROUTES_AREA, SIDEBAR_NAV_AREA } from '@/app/routes'
    import { registry } from '@/contrib/registry'
    import { loadRuntimePlugin, unloadRuntimePlugin } from '@/contrib/runtime-loader'
    import {
      $pluginRecords,
      dropPlugin,
      setPluginEnabled
    } from '@/contrib/plugins-store'

    const pluginFile = process.env.BRAVE_DESKTOP_PLUGIN

    if (!pluginFile) {
      throw new Error('BRAVE_DESKTOP_PLUGIN is required')
    }

    class SourceBlob {
      readonly parts: BlobPart[]
      readonly type: string

      constructor(parts: BlobPart[], options: BlobPropertyBag = {}) {
        this.parts = parts
        this.type = options.type ?? ''
      }
    }

    const originalBlob = globalThis.Blob
    const originalCreateObjectURL = URL.createObjectURL
    const originalRevokeObjectURL = URL.revokeObjectURL

    beforeAll(() => {
      Object.defineProperty(globalThis, 'Blob', {
        configurable: true,
        value: SourceBlob
      })
      Object.defineProperty(URL, 'createObjectURL', {
        configurable: true,
        value: (blob: SourceBlob) => {
          const source = blob.parts.map(part => String(part)).join('')
          return `data:text/javascript;charset=utf-8,${encodeURIComponent(source)}`
        }
      })
      Object.defineProperty(URL, 'revokeObjectURL', {
        configurable: true,
        value: () => undefined
      })
      window.localStorage.clear()
    })

    afterAll(() => {
      unloadRuntimePlugin('brave-search')
      dropPlugin('brave-search')
      Object.defineProperty(globalThis, 'Blob', {
        configurable: true,
        value: originalBlob
      })
      Object.defineProperty(URL, 'createObjectURL', {
        configurable: true,
        value: originalCreateObjectURL
      })
      Object.defineProperty(URL, 'revokeObjectURL', {
        configurable: true,
        value: originalRevokeObjectURL
      })
    })

    test('loads and activates Brave Search through the runtime loader', async () => {
      const source = readFileSync(pluginFile, 'utf8')
      const id = await loadRuntimePlugin(source, 'brave-search', { file: pluginFile })

      expect(id).toBe('brave-search')
      expect($pluginRecords.get()['brave-search']).toMatchObject({
        id: 'brave-search',
        kind: 'disk',
        status: 'disabled'
      })
      expect(registry.getArea(ROUTES_AREA)).toHaveLength(0)
      expect(registry.getArea(SIDEBAR_NAV_AREA)).toHaveLength(0)
      expect(registry.getArea(PALETTE_AREA)).toHaveLength(0)

      await setPluginEnabled('brave-search', true)

      expect($pluginRecords.get()['brave-search']?.status).toBe('loaded')
      expect(registry.getArea(ROUTES_AREA)).toEqual([
        expect.objectContaining({
          id: 'brave-search:brave-search',
          source: 'plugin:brave-search',
          data: { path: '/brave-search' }
        })
      ])
      expect(registry.getArea(SIDEBAR_NAV_AREA)).toEqual([
        expect.objectContaining({
          id: 'brave-search:brave-search-sidebar',
          source: 'plugin:brave-search',
          data: {
            codicon: 'search',
            label: 'Brave Search',
            path: '/brave-search'
          }
        })
      ])
      expect(registry.getArea(PALETTE_AREA)).toEqual([
        expect.objectContaining({
          id: 'brave-search:brave-search-palette',
          source: 'plugin:brave-search',
          data: expect.objectContaining({
            id: 'brave-search.open',
            label: 'Open Brave Search'
          })
        })
      ])
    })
    """
)


def _hermes_python() -> str:
    configured = os.environ.get("HERMES_TEST_PYTHON")
    if configured:
        return configured
    if importlib.util.find_spec("hermes_cli") is not None:
        return sys.executable
    pytest.skip(
        "Hermes is not installed in this environment; set HERMES_TEST_PYTHON "
        "to a current Hermes interpreter"
    )


def _hermes_source() -> Path:
    configured = os.environ.get("HERMES_TEST_SOURCE")
    if configured:
        source = Path(configured)
    else:
        result = subprocess.run(
            [
                _hermes_python(),
                "-c",
                "from pathlib import Path; import hermes_cli; "
                "print(Path(hermes_cli.__file__).resolve().parents[1])",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        source = Path(result.stdout.strip())
    if not source.is_dir():
        pytest.skip(f"Current Hermes source is unavailable at {source}")
    return source


def _run_scenario(tmp_path: Path, *, enabled: bool) -> dict[str, object]:
    hermes_home = tmp_path / "home" / ".hermes"
    backend_root = hermes_home / "plugins" / PLUGIN_ID
    desktop_root = hermes_home / "desktop-plugins" / PLUGIN_ID
    backend_root.parent.mkdir(parents=True)
    desktop_root.parent.mkdir(parents=True)
    backend_root.symlink_to(ROOT, target_is_directory=True)
    desktop_root.symlink_to(ROOT / "desktop", target_is_directory=True)
    assert backend_root.resolve() == ROOT
    assert desktop_root.resolve() == ROOT / "desktop"
    (hermes_home / "config.yaml").write_text(
        json.dumps({"plugins": {"enabled": [PLUGIN_ID] if enabled else []}}),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "HOME": str(tmp_path / "home"),
            "HERMES_HOME": str(hermes_home),
            "HERMES_ENABLE_PROJECT_PLUGINS": "0",
        }
    )
    for name in ("BRAVE_API_KEY", "BRAVE_SEARCH_API_KEY", "TAVILY_API_KEY"):
        env.pop(name, None)

    result = subprocess.run(
        [
            _hermes_python(),
            "-c",
            _SCENARIO,
            "enabled" if enabled else "disabled",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.splitlines()[-1])


def test_current_hermes_runtime_mounts_enabled_plugin_and_hides_disabled_plugin(
    tmp_path: Path,
) -> None:
    enabled = _run_scenario(tmp_path / "enabled", enabled=True)

    assert enabled["mounted"] is True
    assert enabled["package_path"] == str(ROOT / "src" / "hermes_brave_search")
    assert enabled["unauthenticated_status"] == 401
    assert enabled["unauthenticated_body"] == {"detail": "Unauthorized"}
    assert enabled["authenticated_status"] == 200
    assert enabled["authenticated_body"] == {
        "outcome": "results",
        "results": [
            {
                "title": "Hermes Agent",
                "description": "Desktop plugin documentation",
                "url": "https://hermes-agent.nousresearch.com/docs",
                "position": 1,
            }
        ],
    }
    assert enabled["client_calls"] == [
        {"query": "Hermes Agent", "mode": "web", "limit": 5}
    ]

    disabled = _run_scenario(tmp_path / "disabled", enabled=False)

    assert disabled["mounted"] is False
    assert disabled["package_path"] is None
    assert disabled["unauthenticated_status"] == 401
    assert disabled["unauthenticated_body"] == {"detail": "Unauthorized"}
    assert disabled["authenticated_status"] == 404
    assert disabled["authenticated_body"] == {"detail": "Plugin not found"}


def test_desktop_plugin_uses_current_hermes_runtime_contract() -> None:
    hermes_source = _hermes_source()
    desktop_root = hermes_source / "apps" / "desktop"
    vitest = hermes_source / "node_modules" / ".bin" / "vitest"
    if not vitest.is_file():
        pytest.fail(
            "Current Hermes Desktop dependencies are unavailable; run "
            "`npm ci --workspace apps/desktop --ignore-scripts` in HERMES_TEST_SOURCE"
        )

    runtime_test = (
        desktop_root
        / "src"
        / "contrib"
        / f"brave-search-runtime-smoke-{os.getpid()}.test.ts"
    )
    assert not runtime_test.exists()
    runtime_test.write_text(_DESKTOP_LOADER_SMOKE, encoding="utf-8")

    env = os.environ.copy()
    env["BRAVE_DESKTOP_PLUGIN"] = str(ROOT / "desktop" / "plugin.js")
    try:
        result = subprocess.run(
            [
                str(vitest),
                "run",
                "--config",
                "vite.config.ts",
                "--environment",
                "jsdom",
                str(runtime_test.relative_to(desktop_root)),
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=desktop_root,
            env=env,
            timeout=60,
        )
    finally:
        runtime_test.unlink(missing_ok=True)

    assert result.returncode == 0, result.stdout + result.stderr


def test_current_hermes_ci_runs_desktop_integration_proof() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert (
        "tests/test_hermes_plugin_manager.py tests/test_desktop_hermes_integration.py"
        in workflow
    )
