# Brave Search Pro installed

This plugin works best with Brave for search and Tavily for extraction.

The `brave_search` tool also supports Brave's dedicated LLM Context API. Use `mode="llm"` or `mode="context"` for query-to-context chunks, and `mode="both"` for Brave web results plus those context chunks.

If you skipped a key during install, get keys here:

- Brave Search API: <https://brave.com/search/api/>
- Tavily free API key: <https://app.tavily.com/>

For a shell session, export both keys:

```bash
export BRAVE_SEARCH_API_KEY=bsa-your-key-here
export TAVILY_API_KEY=tvly-your-key-here
```

For gateways or services, put both keys in the Hermes environment used by the running process, commonly `~/.hermes/.env`:

```bash
BRAVE_SEARCH_API_KEY=bsa-your-key-here
TAVILY_API_KEY=tvly-your-key-here
```

The plugin also applies a Brave Pro compatibility shim when Hermes loads it:

- `web.backend` and `web.search_backend` are set to `brave-pro` when they are missing or still set to `brave-free`.
- `web.extract_backend` is set to `tavily` when Tavily is credentialed and no extraction provider is selected.
- Older Hermes provider pickers are patched in-process so **Brave Search Pro [pro]** opens selected instead of **Brave Search (Free)** when both share the same Brave API key.

Run the doctor to check the full Brave plus Tavily setup:

```bash
python ~/.hermes/plugins/brave-search/scripts/doctor.py
```

After adding missing keys, ask the doctor to apply safe provider defaults:

```bash
python ~/.hermes/plugins/brave-search/scripts/doctor.py --fix
```

Manual equivalent:

```bash
hermes config set web.backend brave-pro
hermes config set web.search_backend brave-pro
hermes config set web.extract_backend tavily
```

You can also confirm or change this interactively:

```bash
hermes tools
```

In the menu, choose **Reconfigure an existing tool's provider or API key**, then **Web Search & Scraping**. **Brave Search Pro [pro]** should show as the active search provider. Tavily is the recommended extraction backend, but it needs `TAVILY_API_KEY` first.

Restart the gateway after changing plugin or web-provider configuration:

```bash
hermes gateway restart
```
