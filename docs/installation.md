# Installation

## Requirements

- Hermes Agent with plugin support
- Python 3.10 or newer
- Brave Search API key
- Tavily configured in Hermes if you want `web_extract` to keep using Tavily

## Install from a local checkout

```bash
git clone https://github.com/GodsBoy/hermes-brave-search-pro.git
cd hermes-brave-search-pro
uv pip install -e .
```

Then enable the plugin in Hermes:

```bash
hermes plugins enable brave-search
```

If your Hermes install uses direct user plugin directories instead of Python entry points, copy or symlink the checkout into your Hermes plugins directory and restart Hermes.

## Configure credentials

Add your Brave Search key to the Hermes environment:

```bash
BRAVE_SEARCH_API_KEY=bsa-your-key-here
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

## Test locally

```bash
uv venv
uv pip install -e '.[dev]'
uv run pytest
uv run ruff check .
```

Live API tests are intentionally not required. The default suite uses mocked HTTP responses so contributors do not need API quota.
