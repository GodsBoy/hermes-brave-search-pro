# Brave Search Pro installed

This plugin works best with Brave for search. It also owns an optional keyed
Tavily extraction provider for `web_extract`; `TAVILY_API_KEY` remains a
separate optional credential. Hermes Desktop is also optional: finish the
backend setup first, then add the local renderer only if you want the Desktop
page.

## Finish backend setup

Enable the backend with its intentional built-in tool override permission, then
restart the active gateway. Use the same profile for every backend command.

### Default profile

```bash
hermes plugins enable brave-search --allow-tool-override
hermes gateway restart
```

### Named profile

Replace `myprofile` with your profile name. The plugin path, installer profile,
enable command, and gateway restart must all use that same profile.

```bash
hermes --profile myprofile plugins enable brave-search --allow-tool-override
hermes --profile myprofile gateway restart
```

## Desktop Brave Search

The Desktop page is an optional plugin and stays disabled until you enable it
in Hermes Desktop Settings. It is a local renderer, not a backend installer.

After the backend is ready, install the renderer for the selected local profile:

### Default local profile

```bash
~/.hermes/plugins/brave-search/scripts/install-desktop.sh
```

### Named local profile

```bash
HERMES_PROFILE=myprofile \
  ~/.hermes/profiles/myprofile/plugins/brave-search/scripts/install-desktop.sh
```

### Remote backend with local Desktop

When Desktop connects to a remote backend, clone the renderer source on the
Desktop machine, rather than assuming the remote backend checkout exists
locally:

```bash
git clone https://github.com/GodsBoy/hermes-brave-search-pro.git \
  ~/hermes-brave-search-desktop
~/hermes-brave-search-desktop/scripts/install-desktop.sh
```

For a named local profile, run:

```bash
HERMES_PROFILE=myprofile \
  ~/hermes-brave-search-desktop/scripts/install-desktop.sh
```

Keep this checkout in place. The installer creates a symlink from the selected
Desktop profile to its `desktop/` directory, so removing the checkout breaks
the renderer. This flow does not create a local backend link. Deploy, enable,
and restart the Python backend on the remote active profile separately.

The Desktop-only installer creates the selected profile's
`desktop-plugins/brave-search` link and leaves `plugins/brave-search` untouched.
It does not enable the backend, configure credentials, or deploy to a remote
gateway. Enable Brave Search separately in Hermes Desktop Settings. That
Settings toggle controls only the renderer and does not require a gateway
restart.

Brave Desktop search needs only `BRAVE_SEARCH_API_KEY`. Tavily remains an
optional, separate extraction integration. The Desktop surface uses the active
profile, so switched profiles need their own current, enabled, credentialed
Python backend. For a remote backend, install the renderer locally, then deploy
or update the Python plugin on the remote active profile separately, enable it
with `--allow-tool-override`, and restart that remote gateway after its backend
route changes. Desktop loading does not automatically import a project Python
plugin into that gateway.

The `brave_search` tool also supports Brave's dedicated LLM Context API and Brave Place Search API. Use `mode="llm"` or `mode="context"` for query-to-context chunks, `mode="both"` for Brave web results plus those context chunks, `mode="place"` or `mode="local"` for Place Search, and `mode="pois"` or `mode="descriptions"` for follow-up POI details.

Context mode supports options such as `context_count`, `max_tokens`, `max_urls`, `max_snippets`, `freshness`, `country`, `search_lang`, `goggles`, `enable_local`, and `context_threshold_mode`. Place mode supports `latitude`, `longitude`, `location`, `radius`, `count`, `country`, `search_lang`, `ui_lang`, `units`, `safesearch`, and `geoloc`; `pois` and `descriptions` use temporary `ids`, with `pois` also accepting `search_lang`, `ui_lang`, and `units`. Use `context_count` for LLM Context depth; normal `limit` still controls web, news, image, video, and suggestion result counts, while Place Search uses `count` up to 100. Brave bills Place Search requests separately from Web Search.

If you skipped a key during install, get keys here:

- Brave Search API: <https://brave.com/search/api/>
- Tavily free API key: <https://app.tavily.com/>

For a shell session, export the required Brave key:

```bash
export BRAVE_SEARCH_API_KEY=bsa-your-key-here
```

If you want optional keyed Tavily extraction, export its separate key too:

```bash
export TAVILY_API_KEY=tvly-your-key-here
```

For gateways or services, put the Brave key in the Hermes environment used by
the running process, commonly `~/.hermes/.env`. Add the Tavily key there only
when you want keyed extraction:

```bash
BRAVE_SEARCH_API_KEY=bsa-your-key-here
TAVILY_API_KEY=tvly-your-key-here
```

The plugin also applies safe Brave Pro backend defaults after Hermes grants its tool override:

- `web.backend` and `web.search_backend` are set to `brave-pro` when they are missing or still set to `brave-free`.
- `web.extract_backend` is set to `tavily` when Tavily is credentialed and no extraction provider is selected.
- This plugin registers the optional keyed `tavily` provider; `TAVILY_API_KEY` remains separate from the Brave key.
- Current Hermes owns provider picker visibility, and explicit Brave Pro backend settings select **Brave Search Pro [pro]**.

Run the doctor to check the full Brave plus Tavily setup:

```bash
python3 ~/.hermes/plugins/brave-search/scripts/doctor.py
```

These examples use `python3`. If it is unavailable, use the exact interpreter
printed by `./scripts/install.sh`, or substitute another compatible Python 3.11
to 3.13 interpreter.

After adding missing keys, ask the doctor to apply safe provider defaults:

```bash
python3 ~/.hermes/plugins/brave-search/scripts/doctor.py --fix
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

In the menu, choose **Reconfigure an existing tool's provider or API key**, then **Web Search & Scraping**. **Brave Search Pro [pro]** should show as the active search provider. Tavily is the recommended optional extraction backend when `TAVILY_API_KEY` is present.

Restart the gateway after changing plugin or web-provider configuration:

```bash
hermes gateway restart
```
