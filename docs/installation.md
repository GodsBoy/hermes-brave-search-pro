# Installation

## Requirements

- Hermes Agent with plugin support
- Brave Search API key
- Tavily configured in Hermes if you want `web_extract` to keep using Tavily

## Canonical Hermes install

Use Hermes' plugin installer with the GitHub owner/repo shorthand:

```bash
hermes plugins install GodsBoy/hermes-brave-search-pro --enable
```

This installs the plugin into Hermes' plugin directory and enables the plugin named `brave-search`.

## Direct user-plugin install

You can also clone the repository directly into the user plugin directory:

```bash
git clone https://github.com/GodsBoy/hermes-brave-search-pro.git \
  ~/.hermes/plugins/brave-search
hermes plugins enable brave-search
```

For a profile-specific install:

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

## Configure credentials

Add your Brave Search key to the Hermes environment:

```bash
export BRAVE_SEARCH_API_KEY=bsa-your-key-here
```

`BRAVE_API_KEY` is also accepted for compatibility, but `BRAVE_SEARCH_API_KEY` is the documented name.

## Use Brave for search and Tavily for extract

```yaml
plugins:
  enabled:
    - brave-search

web:
  search_backend: "brave-pro"
  extract_backend: "tavily"
```

With this setup:

- `web_search` uses Brave Search Pro.
- `web_extract` keeps using Tavily.
- `brave_search` remains available for richer Brave modes.

Restart the gateway after installing or changing plugin configuration:

```bash
hermes gateway restart
```

## Advanced modes

The explicit `brave_search` tool supports:

- `both`: web results plus Brave answer-context results where available
- `web`: standard Brave web results
- `llm`: Brave answer-context results where available
- `images`: Brave image search
- `news`: Brave news search
- `videos`: Brave video search
- `discussions`: discussion-focused web results
- `suggest`: query suggestions
- `raw`: raw Brave API payload

## Development checkout

```bash
git clone https://github.com/GodsBoy/hermes-brave-search-pro.git
cd hermes-brave-search-pro
uv venv
uv pip install -e '.[dev]'
uv run pytest
uv run ruff check .
```

Live API tests are intentionally not required. The default suite uses mocked HTTP responses so contributors do not need API quota.
