# Contributing to hermes-brave-search-pro

Thanks for contributing.

This is a small, single-purpose Hermes plugin: a Brave Search Pro provider plus an advanced `brave_search` tool. It is correctness-first and review-driven. Keep changes scoped, tested, and easy to reason about. The plugin changes the search backend, not the Hermes tool contract, so be careful with anything that touches the public surface (`web_search` provider behavior, the `brave_search` schema, config flag names).

## Workflow

Preferred flow:

1. Open or reference an issue when the change affects behavior, the tool schema, or config flags.
2. Create a focused branch from `main`.
3. Add or update tests with the change.
4. Run local validation before opening the PR.
5. Open a PR with a clear summary, rationale, and validation section.

Typical branch names:

- `fix/...`
- `feat/...`
- `docs/...`
- `refactor/...`
- `test/...`

## Development setup

This project uses [uv](https://docs.astral.sh/uv/). From a fresh checkout:

```bash
git clone https://github.com/GodsBoy/hermes-brave-search-pro.git
cd hermes-brave-search-pro
uv venv
uv pip install -e '.[dev]'
uv run ruff check .
uv run pytest
```

The test suite mocks Brave HTTP responses, so you do not need a Brave API key or live quota to develop or run tests.

## Commits

Prefer clear, conventional-style subjects:

- `fix: ...`
- `feat: ...`
- `docs: ...`
- `refactor: ...`
- `test: ...`

Keep commits focused. Avoid mixing unrelated cleanup into the same change.

## Pull Requests

Open small PRs when possible. Large PRs are harder to review and easier to get wrong.

PR titles should be descriptive and usually follow the same style as commit subjects.

PR bodies use the template in `.github/PULL_REQUEST_TEMPLATE.md`, which GitHub pre-fills for new PRs. If you skip a validation item, leave it unchecked and explain why in Notes.

Good PRs are:

- accurate about what is actually implemented
- honest about scope
- explicit about tradeoffs
- backed by tests

Do not claim behavior that is only partially implemented. If a mode, normalisation path, or fix only applies to one Brave response shape, say that clearly.

## Validation

Default validation for code changes:

```bash
uv pip install -e '.[dev]'
uv run ruff check .
uv run pytest
git diff --check
```

If your PR only touches a narrow surface area, include the focused command too. For example, when changing the tool handler:

```bash
uv run pytest tests/test_tools.py
```

Install or script changes should also verify the install script syntax:

```bash
bash -n scripts/install.sh
```

Workflow changes (`.github/workflows/`) should also run:

```bash
actionlint
```

CI runs `ruff check .` and `pytest` on every pull request, so a green local run should match CI.

## Testing expectations

- behavior changes should come with tests
- bug fixes should include a regression test when practical
- new `brave_search` modes or response shapes should be covered with a mocked Brave payload
- keep tests readable; the existing suite mocks HTTP rather than calling Brave, so follow that pattern

## Review expectations

Before requesting review:

- rebase or merge `main` so the branch is current
- resolve conflicts locally
- make sure the PR description matches the branch exactly
- ensure CI is expected to pass from the current head

Reviewers will check:

- correctness
- edge cases (empty results, missing fields, Brave error payloads)
- test coverage
- whether the implementation matches the claimed behavior
- whether the change is appropriately scoped

## Scope guidelines

Priority order:

1. correctness
2. regressions
3. operator safety (credentials, config defaults)
4. maintainability
5. new features

Backwards-compatible, well-tested changes are preferred. Avoid breaking the `web_search` provider contract or renaming config flags without flagging it clearly for review.

## Security

- Never commit a Brave API key, `.env` file, or any other credential.
- `BRAVE_SEARCH_API_KEY` is the documented variable name (`BRAVE_API_KEY` is accepted as a compatibility fallback). Read credentials from the environment, never hardcode them.
- Do not log secrets or full request URLs that embed credentials.

## Documentation

Update docs when you change:

- the `brave_search` tool schema or its modes
- configuration flags (`web.search_backend`, `web.extract_backend`)
- the install flow or `scripts/install.sh`
- expected operator workflows

Keep `README.md` and `docs/` in sync with behavior in the same PR.

## Questions

If you are unsure whether something should be an issue first, open the issue. It is cheaper than reviewing the wrong PR.
