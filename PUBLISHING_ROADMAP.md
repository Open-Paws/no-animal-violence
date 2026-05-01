# Publishing Roadmap — npm + VS Code Marketplace

This document tracks the 9-phase roadmap to bring the NAV ecosystem to a publish-ready state for `eslint-plugin-no-animal-violence` (npm) and `vscode-no-animal-violence` (VS Code Marketplace). See [issue #70](https://github.com/Open-Paws/no-animal-violence/issues/70) for the full audit findings.

## Current state (as of 2026-05-01)

- Canonical `rules.yaml`: **162 rules**
- Most downstream repos: **158 rules** (4 industrial fish confinement rules added in #63 not yet propagated due to blocked sync PRs)
- `no-animal-violence-action`: **162 rules** (sync PR #39 merged 2026-04-26)

## Dependency graph

```
Phase 1 (regex fixes in canonical rules.yaml)  [PR #71 — open]
        |
        v
Phase 2 (re-run propagate.yml — needs SYNC_TOKEN)  [Sam action]
        |
        v
Phase 3a (merge action sync PR FIRST)  [Sam action]
        |
        v
Phase 3b-c (re-run nav-check, merge other sync PRs in parallel)  [Sam action]
        |
        +---> Phase 4 (cut pre-commit tag, bump reviewdog)  [Sam action]
        |
        +---> Phase 5 (namespace fixes — ESLint + VS Code)  [PRs open]
                  |
                  v
            Phase 6 (tests + publish workflows)  [PRs open]
                  |
                  v     <--- Phase 7 (credentials, parallel)  [Sam action]
                  |
                  v
            Phase 8 (first release tags)  [Sam action]
                  |
                  v
            Phase 9 (long-term hardening)  [backlog]
```

## Phase checklist

### Phase 1 — Fix regex bugs in canonical `rules.yaml`

**Owner: Gary (complete)**  
PR: [#71](https://github.com/Open-Paws/no-animal-violence/pull/71) — open, all CI green

Two regex bugs in the industrial fish confinement rules added by #63, both surfaced by CodeRabbit on active sync PRs:

- **`stocking-density`**: old pattern `stocking\s+density(ies)?` never matched the plural form. Fixed to `\bstocking\s+densit(?:y|ies)\b`.
- **`harvest-size`**: old pattern was too broad — matched in business writing unrelated to intensive fish confinement operations. Fixed to scope the false-positive case to fish species context via species qualifier.

### Phase 2 — Re-run propagation from updated canonical

**Owner: Sam**

After Phase 1 merges:

1. Run `gh workflow run propagate.yml --repo Open-Paws/no-animal-violence` (requires `SYNC_TOKEN`)
2. Verify 8 fresh sync PRs appear with the new canonical SHA, each containing 162 rules + the `ignore_files` fix from #66

### Phase 3 — Merge sync PRs in dependency order

**Owner: Sam**

The `no-animal-violence-action` repo must merge first — every other consumer's `nav-check` pulls `Open-Paws/no-animal-violence-action@main`. After the action repo merges, the inline `ignore_files` fix ships and the other consumers' `nav-check` failures clear.

- **3a.** Merge `no-animal-violence-action` sync PR first
- **3b.** Re-run `nav-check` on the remaining sync PRs (or rebase to pick up the new action.yml)
- **3c.** Merge consumer sync PRs (can be parallel): `eslint-plugin`, `vscode`, `semgrep`, `pre-commit`, `danger`, `vale`
- **3d.** For Vale: run a coherence check on the ~79 rules about to be removed (currently deployed Vale file predates the canonical refactor and shares only 9 rule names). File follow-up issues for any worth porting back to canonical before merging.

### Phase 4 — Bring reviewdog up to date

**Owner: Sam**

- **4a.** After `pre-commit` sync merges, cut a new release tag (e.g. `v0.3.0`) on `no-animal-violence-pre-commit`
- **4b.** Update `reviewdog-no-animal-violence`'s `action.yml` to bump the pinned tag (`v0.2.0` → `v0.3.0`)
- **4c.** Long-term: extend `gen_reviewdog.py` to read the latest pre-commit tag dynamically

### Phase 5 — Fix namespace bugs in publishing targets

**Owner: Gary (PRs open)**

Non-generated bugs that prevent published packages from working out of the box:

- **ESLint plugin**: PR [eslint-plugin-no-animal-violence#38](https://github.com/Open-Paws/eslint-plugin-no-animal-violence/pull/38) — replaces stale `speciesism` plugin name with `no-animal-violence` in `lib/index.js`
- **VS Code extension**: PR [vscode-no-animal-violence#37](https://github.com/Open-Paws/vscode-no-animal-violence/pull/37) — renames `speciesism.*` settings to `no-animal-violence.*` in `package.json`

These PRs are open and ready for review.

### Phase 6 — Add tests + CI + publish workflows

**Owner: Gary (PRs open)**

- **ESLint plugin**: PR [eslint-plugin-no-animal-violence#39](https://github.com/Open-Paws/eslint-plugin-no-animal-violence/pull/39) — RuleTester suite (Node 18/20/22 x ESLint 7/8/9 matrix), publish workflow on `v*` tag push
- **VS Code extension**: PR [vscode-no-animal-violence#38](https://github.com/Open-Paws/vscode-no-animal-violence/pull/38) — extension smoke tests, publish workflow on `v*` tag push

These PRs are open and ready for review.

### Phase 7 — Provision credentials

**Owner: Sam (one-time setup)**

For npm:
1. Create org `open-paws` at npmjs.com (free for public packages)
2. Generate Automation token (Access Tokens > Generate New Token > Automation type — bypasses 2FA, intended for CI)
3. Add as `NPM_TOKEN` secret on `Open-Paws/eslint-plugin-no-animal-violence`

For VS Code Marketplace:
1. Create publisher `open-paws` at marketplace.visualstudio.com/manage
2. Generate Azure DevOps PAT at dev.azure.com (User Settings > Personal Access Tokens > New Token, scope: Marketplace > Manage, org: All accessible, expiry: 1 year)
3. Add as `VSCE_PAT` secret on `Open-Paws/vscode-no-animal-violence`
4. Calendar reminder ~2 weeks before expiry for both tokens

### Phase 8 — Cut first releases

**Owner: Sam**

After Phases 6 + 7 are complete:

1. `git tag v0.1.0 && git push origin v0.1.0` on `eslint-plugin-no-animal-violence` — publish workflow fires automatically
2. `git tag v0.1.0 && git push origin v0.1.0` on `vscode-no-animal-violence` — publish workflow fires automatically
3. Verify: `npm view eslint-plugin-no-animal-violence` shows v0.1.0
4. Verify: Marketplace listing visible at marketplace.visualstudio.com search "animal violence"
5. Smoke test: `npm install eslint-plugin-no-animal-violence` in a fresh project, confirm a flagged phrase is detected correctly (e.g. the `stocking-density` rule fires on the documented phrase)

### Phase 9 — Long-term hardening (post-launch, backlog)

**Owner: Gary (future)**

- Wire `tools/check_consistency.py` into a `consistency.yml` workflow that runs after each `propagate.yml` and fails CI if downstream rule counts drift from canonical
- Document a "release a rule change" runbook in `SYNC.md`
- Consider GitHub App in place of `SYNC_TOKEN` PAT (no expiry, scoped to org, audit trail)
- Bot-driven sync PR auto-merge for low-risk diffs (matches generated-file manifest exactly)

## Sync PR status (as of 2026-05-01)

| Repo | Sync PR | State | Target rules |
|---|---|---|---|
| `no-animal-violence-action` | [#39](https://github.com/Open-Paws/no-animal-violence-action/pull/39) | MERGED 2026-04-26 | 162 |
| `eslint-plugin-no-animal-violence` | [#36](https://github.com/Open-Paws/eslint-plugin-no-animal-violence/pull/36) | OPEN, BLOCKED (regex bugs) | 162 |
| `vscode-no-animal-violence` | [#33](https://github.com/Open-Paws/vscode-no-animal-violence/pull/33) | OPEN | 162 |
| `semgrep-rules-no-animal-violence` | [#36](https://github.com/Open-Paws/semgrep-rules-no-animal-violence/pull/36) | OPEN, BLOCKED (regex bugs) | 162 |
| `no-animal-violence-pre-commit` | [#35](https://github.com/Open-Paws/no-animal-violence-pre-commit/pull/35) | CLOSED (manually) | 162 |
| `danger-plugin-no-animal-violence` | [#32](https://github.com/Open-Paws/danger-plugin-no-animal-violence/pull/32) | OPEN | 162 |
| `vale-no-animal-violence` | [#33](https://github.com/Open-Paws/vale-no-animal-violence/pull/33) | OPEN | 162 |
| `reviewdog-no-animal-violence` | — | inherits pre-commit (pinned to v0.2.0) | — |

> After Phase 1 merges and propagation re-runs, all OPEN sync PRs become stale. Close them and merge the fresh PRs from the re-propagation run.
