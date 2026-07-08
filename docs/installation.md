# Installation

## Requirements

- Hermes Agent with plugin support
- Brave Search API key
- Tavily API key and Hermes' bundled `web-tavily` plugin if you want the recommended `web_extract` pairing. Tavily offers a free API key at <https://app.tavily.com/>.

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
- `web-tavily` plus `TAVILY_API_KEY` for Tavily-backed `web_extract`.

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

Enable the optional Tavily extraction plugin when you want `web_extract` to use Tavily:

```bash
hermes plugins enable web-tavily
```

## Use Brave for search and Tavily for extract

The plugin applies safe defaults when Hermes loads it. If Brave is credentialed, missing or still-free web search settings are moved to Brave Pro. If Tavily is credentialed and no extraction provider is selected, extraction is set to Tavily. The separate bundled `web-tavily` plugin must still be enabled for Tavily `web_extract` to run.

Run the doctor explicitly to check both sides:

```bash
python ~/.hermes/plugins/brave-search/scripts/doctor.py
```

After adding missing keys, apply safe provider defaults:

```bash
python ~/.hermes/plugins/brave-search/scripts/doctor.py --fix
```

The interactive Hermes tools flow remains available for visual confirmation:

```bash
hermes tools
```

Then choose **Reconfigure an existing tool's provider or API key**, then **Web Search & Scraping**. **Brave Search Pro [pro]** should show as the active search provider. Tavily is the recommended extraction backend, but it needs `web-tavily` enabled and `TAVILY_API_KEY` present before `web_extract` can use it.

Equivalent manual config:

```yaml
plugins:
  enabled:
    - brave-search
    - web-tavily  # optional, only needed for Tavily web_extract

web:
  backend: "brave-pro"
  search_backend: "brave-pro"
  extract_backend: "tavily"
```

Or set those keys directly:

```bash
hermes config set web.backend brave-pro
hermes config set web.search_backend brave-pro
hermes plugins enable web-tavily  # optional, only needed for Tavily web_extract
hermes config set web.extract_backend tavily
```

With this setup:

- `web_search` uses Brave Search Pro.
- `web_extract` keeps using Tavily.
- `brave_search` remains available for richer Brave modes, including Brave's dedicated LLM Context API through `mode="llm"` or `mode="context"`, and Brave Place Search API modes through `mode="place"`, `mode="local"`, `mode="pois"`, or `mode="descriptions"`.

Restart the gateway after installing or changing plugin configuration:

```bash
hermes gateway restart
```

## Advanced modes

The explicit `brave_search` tool supports:

- `both`: Brave web results plus dedicated LLM Context API chunks
- `web`: standard Brave web results
- `llm`: Brave LLM Context API chunks from `/res/v1/llm/context`
- `context`: alias for `llm`, useful when you want the dedicated context endpoint explicitly
- `images`: Brave image search
- `news`: Brave news search
- `videos`: Brave video search
- `discussions`: discussion-focused web results
- `suggest`: query suggestions
- `place`: Brave Place Search through `/res/v1/local/place_search`
- `local`: alias for `place`, including Explore Mode when no query is supplied
- `pois`: follow-up POI details from `/res/v1/local/pois`
- `descriptions`: follow-up POI descriptions from `/res/v1/local/descriptions`
- `raw`: raw Brave API payload

Context mode supports advanced Brave retrieval controls:

```python
brave_search(
    query="Hermes Agent plugin system",
    mode="context",
    context_count=20,
    max_tokens=8192,
    max_urls=10,
    max_snippets=40,
    freshness="pw",
    country="US",
    search_lang="en",
    context_threshold_mode="balanced",
)
```

Use `context_count` for LLM Context depth. The normal `limit` option still controls web, news, image, video, and suggestion result counts. Place Search uses `count` for up to 100 results, and `pois` or `descriptions` use temporary POI IDs returned by Place Search. Brave bills Place Search requests separately from Web Search. Tavily remains the recommended `web_extract` backend because Brave Search Pro is search and context only in Hermes.

Place Search example:

```python
brave_search(
    query="coffee shops",
    mode="place",
    location="Cape Town South Africa",
    count=25,
    units="metric",
)
brave_search(mode="descriptions", ids=["temporary-poi-id-from-place-result"])
```

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
