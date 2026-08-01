# Packaged Hermes Desktop verification

Source review run: `20260731-213147-1ff3a985`

## Status

- Tracking issue: [#6 Verify Brave Search in packaged Hermes Desktop](https://github.com/GodsBoy/hermes-brave-search-pro/issues/6)
- Status: Completed on 31 July 2026
- Follow-up: [PR #8](https://github.com/GodsBoy/hermes-brave-search-pro/pull/8) fixed the two Brave-owned low-contrast labels found during verification.

The plugin was exercised against an actual `electron-builder` Hermes Desktop package with the renderer loaded from `app.asar` and `app.isPackaged` active.

Verified in isolated default and named profiles:

- Desktop plugin discovery in Settings
- Enable, disable and re-enable flows
- Sidebar and command-palette contributions
- Idle and empty-query validation
- Loading, results, empty, missing-credential, backend-unavailable, rate-limit and retryable-error states
- Safe result-link handling, including rejection of a `javascript:` URL
- Folder reconciliation and live `plugin.js` reload
- Named-profile Desktop root resolution and profile-scoped backend API mounting

The state matrix used a deterministic local backend fixture. No Brave credential or external Brave request was used, and the live Hermes profile and gateway were untouched.
