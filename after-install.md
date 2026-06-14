# Brave Search Pro installed

Next, configure Hermes to use Brave for search and Tavily for extraction:

```bash
hermes tools
```

In the menu:

1. Choose **Reconfigure an existing tool's provider or API key**.
2. Choose **Web Search & Scraping**.
3. Select **Brave Search Pro [pro]** as the search provider.
4. Keep or select **Tavily [paid]** as the extraction provider.

If you have not set up Tavily yet, get a free API key at:

<https://app.tavily.com/>

Then save it where the Hermes process can read it:

```bash
export TAVILY_API_KEY=tvly-your-key-here
```

For gateways or services, put both keys in the Hermes environment used by the running process, commonly `~/.hermes/.env`:

```bash
BRAVE_SEARCH_API_KEY=bsa-your-key-here
TAVILY_API_KEY=tvly-your-key-here
```

Restart the gateway after changing plugin or web-provider configuration:

```bash
hermes gateway restart
```
