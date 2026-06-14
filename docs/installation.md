# Installation

## Requirements

- Hermes Agent with plugin support
- Brave Search API key
- Tavily API key if you want the recommended `web_extract` pairing. Tavily offers a free API key at <https://app.tavily.com/>.

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

### Search plus extraction credentials

This plugin provides Brave Search Pro for discovery. Brave is search-only in Hermes, so the recommended default pairing is:

- `BRAVE_SEARCH_API_KEY` for Brave-backed `web_search` and `brave_search`.
- `TAVILY_API_KEY` for Tavily-backed `web_extract`.

Get keys here:

- Brave Search API: <https://brave.com/search/api/>
- Tavily free API key: <https://app.tavily.com/>

Tavily's free plan currently includes 1,000 API credits per month and does not require a credit card.

Add the keys to the Hermes environment:

```bash
export BRAVE_SEARCH_API_KEY=bsa-your-key-here
export TAVILY_API_KEY=tvly-your-key-here
```

For gateways or services, make sure those variables are available to the running Hermes process. A common local setup is `~/.hermes/.env`:

```bash
BRAVE_SEARCH_API_KEY=bsa-your-key-here
TAVILY_API_KEY=tvly-your-key-here
```

`BRAVE_API_KEY` is also accepted for compatibility, but `BRAVE_SEARCH_API_KEY` is the documented name.

## Use Brave for search and Tavily for extract

The plugin applies safe defaults when Hermes loads it. If Brave is credentialed, missing or still-free web search settings are moved to Brave Pro; if Tavily is credentialed and no extraction provider is selected, extraction is set to Tavily. You can also run the helper explicitly:

```bash
python ~/.hermes/plugins/brave-search/scripts/configure.py
```

The interactive Hermes tools flow remains available:

```bash
hermes tools
```

Then choose:

1. **Reconfigure an existing tool's provider or API key**
2. **Web Search & Scraping**
3. **Brave Search Pro [pro]** for search
4. **Tavily [paid]** for extraction

Equivalent manual config:

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
