## Summary
-

## Why
-

## Validation
- [ ] Focused validation: `<command>` -> `<result>`
- [ ] Default validation:
  - [ ] `uv pip install -e '.[dev]'`
  - [ ] `uv run ruff check .`
  - [ ] `uv run pytest`
  - [ ] `git diff --check`
- [ ] Install-flow validation, if `scripts/` changed: `bash -n scripts/install.sh`
- [ ] Workflow validation, if `.github/workflows/` changed: `actionlint`

## Notes
-

Refs #
