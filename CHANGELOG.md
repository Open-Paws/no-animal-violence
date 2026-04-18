# Changelog

## [Unreleased] — Push-model automation

### Added
- `rules.yaml` — enriched canonical source of truth, replacing `woke/.woke.yaml` as the file generators read from. Fields: `name`, `terms`, `alternatives`, `severity`, `category`, `note`, `word_boundary`, `regex`, `context_suppressions`.
- `tools/generators/` package with importable generator modules:
  - `loader.py` — shared YAML loader and `Rule` dataclass
  - `gen_semgrep.py` — generates 4 Semgrep rule files (generic, Python, JS, Go)
  - `gen_vale.py` — generates Vale substitution files for downstream and canonical
  - `gen_pre_commit.py` — generates the pre-commit hook
  - `gen_action.py` — generates the GitHub Action `action.yml` with embedded woke rules
  - `gen_reviewdog.py` — generates the reviewdog `action.yml` (static, no phrase list)
  - `gen_woke.py` — regenerates `woke/.woke.yaml` from `rules.yaml`
  - `gen_eslint.js` — generates ESLint plugin phrase map
  - `gen_danger.js` — generates Danger plugin TypeScript patterns
  - `gen_vscode.js` — generates VS Code extension patterns
- `tools/generate_all.py` — orchestrates all generators; outputs to `build/`
- `tools/propagate.py` — opens sync PRs against all 8 downstream repos
- `tools/generators/tests/` — golden-file test suite for generators
- `.github/workflows/propagate.yml` — CI workflow to propagate rules on demand
- `SYNC.md` — documents PAT setup and the push-model workflow

### Changed
- `tools/check_consistency.py` — rewritten to read from `rules.yaml` via `loader.py` with fallback to `woke/.woke.yaml`; added `--skip-clone` flag

### Notes
- The `propagate.yml` workflow is gated behind `workflow_dispatch` — it will not auto-fire on push to `main` until the commented-out `push:` trigger is uncommented (see `SYNC.md`).
- Run `pytest tools/generators/` after merging to verify generators against the mini fixture.
- Run `python tools/generate_all.py` to produce full output in `build/`.
