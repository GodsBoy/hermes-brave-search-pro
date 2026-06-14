# Brave Search Pro for Hermes Agent

<p align="center">
  <img src="docs/assets/hermes-brave-search-pro-banner.png" alt="Hermes Brave Search Pro banner" width="920">
</p>

<p align="center">
  <img src="docs/assets/brave-hermes-hero.png" alt="Brave Search Pro for Hermes Agent infographic" width="920">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-F97316.svg"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-2563EB.svg">
  <img alt="Hermes plugin" src="https://img.shields.io/badge/Hermes-plugin-111827.svg">
  <img alt="Brave Search Pro" src="https://img.shields.io/badge/Brave-Search%20Pro-FF5A1F.svg">
</p>

Brave Search Pro as a first-class Hermes Agent plugin.

Brave handles fast, index-backed discovery for `web_search`, Tavily keeps doing extraction, and the explicit `brave_search` tool adds Brave-specific modes (images, news, videos, and more) when you want them.

## Why this exists

Hermes already separates search from extraction. This plugin leans into that design:

- **Discovery:** `web_search` uses Brave Search Pro through the `brave-pro` backend.
- **Extraction:** `web_extract` can stay on Tavily through `web.extract_backend`.
- **Advanced search:** `brave_search` exposes Brave modes that do not fit the standard `web_search` contract.
- **No source patching:** install the plugin, let its compatibility shim configure safe defaults, and keep updating Hermes normally.

## Features

- Hermes web-search provider named `brave-pro`
- Runtime compatibility shim that safely prefers Brave Pro over Brave Free when both share the same Brave API key
- Advanced Hermes tool named `brave_search`
- Search-only provider so Tavily remains the extraction backend
- Shared Brave client with structured errors and response normalisation
- Mocked test suite that does not require live Brave credentials
- Public-ready docs, examples, and visual explanation

## Quick start

Canonical Hermes install:

```bash
hermes plugins install GodsBoy/hermes-brave-search-pro --enable
```

During install, Hermes prompts for the plugin's recommended credentials:

- `BRAVE_SEARCH_API_KEY` for Brave-backed search
- `TAVILY_API_KEY` for Tavily-backed extraction

If you skipped either prompt, export them in the environment Hermes runs with:

```bash
export BRAVE_SEARCH_API_KEY=bsa-your-key-here
export TAVILY_API_KEY=tvly-your-key-here
```

Brave Search Pro is search-only by design, so Tavily stays the recommended `web_extract` pairing (it has a free tier, see [app.tavily.com](https://app.tavily.com/)). When Hermes loads the plugin it applies safe defaults: Brave Pro for `web_search` when Brave is credentialed, and Tavily for `web_extract` when a Tavily key is present and no extraction provider is already selected.

Verify the setup with the doctor:

```bash
python ~/.hermes/plugins/brave-search/scripts/doctor.py
```

It reports what is configured and applies safe defaults with `--fix`. See [Run the doctor](#run-the-doctor) under Troubleshooting for the full check list.

Then use the clean pairing:

```python
web_search(query="Hermes Agent plugins", limit=5)   # Brave Search Pro
web_extract(urls=["https://example.com/article"])  # Tavily
brave_search(query="Hermes Agent", mode="news")   # Brave-specific mode
```

Restart the gateway after installing or changing plugin configuration:

```bash
hermes gateway restart
```

## Verify the provider

To confirm the active provider visually:

```bash
hermes tools
```

In the interactive menu, choose **Reconfigure an existing tool's provider or API key**, then **Web Search & Scraping**. The search provider should show **Brave Search Pro [pro]** as active. Tavily is an extraction backend, so make sure `TAVILY_API_KEY` is present before expecting Tavily-backed `web_extract` to work.

<p align="center">
  <img src="docs/assets/hermes-tools-reconfigure-provider.jpg" alt="Hermes tools menu with Reconfigure an existing tool's provider or API key selected" width="760">
</p>

<p align="center">
  <img src="docs/assets/hermes-tools-web-search-scraping.jpg" alt="Hermes tools menu with Web Search and Scraping selected" width="760">
</p>

<p align="center">
  <img src="docs/assets/hermes-tools-brave-pro-provider.jpg" alt="Hermes provider menu showing Brave Search Pro as an active provider option" width="920">
</p>

The provider should appear as:

```text
Brave Search Pro [pro] - Brave-backed discovery for Hermes web_search. Pair with Tavily for web_extract.
```

## Manual configuration

The plugin sets safe defaults automatically, but you can configure the pairing explicitly. In your `hermes` config:

```yaml
plugins:
  enabled:
    - brave-search

web:
  backend: "brave-pro"
  search_backend: "brave-pro"
  extract_backend: "tavily"
```

Or set those keys directly:

```bash
hermes config set web.backend brave-pro
hermes config set web.search_backend brave-pro
hermes config set web.extract_backend tavily
```

## Advanced `brave_search` modes

`brave_search` accepts:

- `both`: web results plus Brave answer-context payloads where available
- `web`: standard Brave web results
- `llm`: Brave answer-context payloads where available
- `images`: image search
- `news`: news search
- `videos`: video search
- `discussions`: discussion-focused results
- `suggest`: query suggestions
- `raw`: raw Brave API payload for debugging and exploration

Example:

```python
brave_search(query="Hermes Agent plugin system", mode="both", limit=5)
```

## Architecture

```mermaid
flowchart TB
  Agent[Hermes agent] --> BuiltIn[web_search]
  Agent --> Advanced[brave_search]
  BuiltIn --> Registry[Hermes web search registry]
  Registry --> Brave[brave-pro provider]
  Advanced --> Client[Shared Brave client]
  Brave --> Client
  Client --> API[Brave Search Pro API]
  Agent --> Extract[web_extract]
  Extract --> Tavily[Tavily backend]
```

The standard Hermes `web_search` tool stays standard. The plugin changes the backend, not the tool contract. Richer Brave modes are explicit, which keeps normal search simple and makes advanced use intentional.

## Repository layout

```text
src/hermes_brave_search/
├── __init__.py     # Hermes registration entry point
├── client.py       # Brave API client and normalisation
├── compat.py       # Runtime compatibility and safe config defaults
├── configure.py    # Explicit configuration helper
├── doctor.py       # Setup diagnostics for Brave and Tavily
├── provider.py     # Hermes web search provider
├── schemas.py      # Tool schema for brave_search
└── tools.py        # Tool handler
```

## Install options

Canonical Hermes install:

```bash
hermes plugins install GodsBoy/hermes-brave-search-pro --enable
```

Update an existing install:

```bash
hermes plugins update brave-search
```

Direct user-plugin install:

```bash
git clone https://github.com/GodsBoy/hermes-brave-search-pro.git \
  ~/.hermes/plugins/brave-search
hermes plugins enable brave-search
```

Profile-specific install:

```bash
git clone https://github.com/GodsBoy/hermes-brave-search-pro.git \
  ~/.hermes/profiles/myprofile/plugins/brave-search
hermes --profile myprofile plugins enable brave-search
```

From an existing checkout, install a symlink:

```bash
./scripts/install.sh
# Optional profile-aware install
HERMES_PROFILE=myprofile ./scripts/install.sh
```

For development only:

```bash
git clone https://github.com/GodsBoy/hermes-brave-search-pro.git
cd hermes-brave-search-pro
uv venv
uv pip install -e '.[dev]'
uv run pytest
uv run ruff check .
```

The default tests mock Brave HTTP responses. Live API calls are not part of the normal test path, so public contributors do not need Brave API quota.

## Troubleshooting

### Run the doctor

Use the doctor command when setup does not look right:

```bash
python ~/.hermes/plugins/brave-search/scripts/doctor.py
```

It checks:

- `BRAVE_SEARCH_API_KEY` or compatibility fallback `BRAVE_API_KEY`
- `TAVILY_API_KEY`
- `web.backend`
- `web.search_backend`
- `web.extract_backend`
- the runtime compatibility shim that keeps Brave Pro selected when Brave Free shares the same API key

After adding missing keys, ask the doctor to apply safe provider defaults:

```bash
python ~/.hermes/plugins/brave-search/scripts/doctor.py --fix
```

Use `--force` with care if you intentionally want to overwrite existing web-provider choices:

```bash
python ~/.hermes/plugins/brave-search/scripts/doctor.py --fix --force
```

### Hermes cannot see the provider

Check that the plugin is enabled and Hermes was restarted after installation:

```bash
hermes plugins enable brave-search
```

Then confirm your config uses the provider name exactly:

```yaml
web:
  backend: "brave-pro"
  search_backend: "brave-pro"
```

### Search says the API key is missing

Export `BRAVE_SEARCH_API_KEY` in the environment used by the Hermes process. `BRAVE_API_KEY` is accepted as a compatibility fallback, but `BRAVE_SEARCH_API_KEY` is the documented name.

### Extraction stopped using Tavily

Set extraction explicitly:

```yaml
web:
  backend: "brave-pro"
  search_backend: "brave-pro"
  extract_backend: "tavily"
```

Do not rely on `web.backend` for this pairing because that single fallback applies to both capabilities.

## License

MIT. See [LICENSE](LICENSE).
