# Brave Search Pro installed

This plugin works best with Brave for search and Tavily for extraction.

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

Persist the recommended web providers:

```bash
hermes config set web.search_backend brave-pro
hermes config set web.extract_backend tavily
```

You can also confirm or change this interactively:

```bash
hermes tools
```

In the menu:

1. Choose **Reconfigure an existing tool's provider or API key**.
2. Choose **Web Search & Scraping**.
3. Select **Brave Search Pro [pro]** as the search provider.
4. Keep or select **Tavily [paid]** as the extraction provider.

Restart the gateway after changing plugin or web-provider configuration:

```bash
hermes gateway restart
```
