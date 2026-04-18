# no-animal-violence

Rule files for detecting speciesist language in code, documentation, and prose. Part of the Open Paws speciesist language detection suite. Compatible with woke, alex/retext-equality, and Vale.

## Quick Start

Rules are static YAML/config files — no build step required. Copy or reference the relevant directory for your tool:

- **woke**: use `woke/.woke.yaml`
- **alex/retext-equality**: use files in `alex/`
- **Vale**: use the `vale/Speciesism/` style package

## Architecture

`rules.yaml` is the **single canonical source of truth**. All rule files in `alex/`, `woke/`, and `vale/Speciesism/` are generated from it — do not edit them directly. Run `tools/generate_all.py` to regenerate. All downstream adapter repos receive rule updates via the `propagate.yml` CI workflow.

## Key Files

| File | Description |
|------|-------------|
| `rules.yaml` | **Edit this.** Canonical rule definitions for all downstream formats. |
| `woke/.woke.yaml` | Generated: woke scanner config |
| `alex/animal-violence.yml` | Generated: alex/retext-equality rules (animal-violence category) |
| `alex/industry-euphemisms.yml` | Generated: alex/retext-equality rules (industry-euphemism category) |
| `vale/Speciesism/AnimalIdioms.yml` | Generated: Vale substitution rules (animal-violence category) |
| `vale/Speciesism/IndustryEuphemisms.yml` | Generated: Vale substitution rules (industry-euphemism category) |

## Organizational Context

This repo is the **canonical rule dictionary** for the entire no-animal-violence suite. Every downstream adapter (Vale, ESLint, Semgrep, VS Code, pre-commit, GitHub Action, reviewdog, Danger, Alex, Woke) consumes or mirrors these definitions. Rule additions here should propagate to all consumers.

**Strategic significance (Lever 1 + Lever 3):** This is a concrete Lever 3 tool — it embeds animal welfare standards into the development process itself. Every developer who installs an adapter becomes aware of speciesist language patterns. The suite is intervention #8 from the 25 Ranked Interventions (Animal-Friendly Data Labelling Standards) made concrete.

**Academic backing:** Rules are backed by peer-reviewed research on AI speciesism and language bias. Key citations:
- Hagendorff et al. (2023–2025) — speciesist bias in LLM outputs; doi:10.1007/s43681-023-00380-w
- Takeshita et al. (2022) — language normalization of animal exploitation
- Leach et al. (2023) — moral circle expansion and language framing

These citations appear in rule metadata (`references:` field) and give the suite credibility in Lever 3 outreach to development teams and AI labs.

**MCP ecosystem integrations:**
- `lbr8-mcp-constraints` — bundles 12 offline NAV patterns sourced from this repo as a `StaticConstraintSource`. These patterns run in air-gapped/offline contexts where the full Semgrep ruleset cannot be loaded. When updating rules here, check whether the 12 bundled patterns in `lbr8-mcp-constraints` need updating. See `repos/lbr8-mcp-constraints` in the strategy repo.
- `mcp-server-nav-language` — loads `semgrep-rules-no-animal-violence` YAML at startup for the content pipeline NAV gate (PR #7). Canonical patterns flow: this repo → `project-compassionate-code` generator → `semgrep-rules-no-animal-violence` → `mcp-server-nav-language`.

**Current org priorities relevant to this repo:**
- The suite has zero platform presence despite being a shipped product. Planned: bootcamp setup instructions (VS Code extension + pre-commit hook), guild developer onboarding, platform CI. See `ecosystem/integration-todos.md` §27a.
- Suite maintenance has **no named owner** as of 2026-04-02. The 65+ rules need ongoing false-positive tuning and new term additions — ideal F/E-rank quests in the Guild pipeline.
- Adoption metrics (npm downloads, VS Code marketplace installs, GitHub Action usage) are not yet tracked. This is a Lever 3 measurement gap.
- Compassionate Code integration is in place — the CC scanner uses these rules to find speciesist language in open-source repos. Stronger rules here directly improve CC scanner output.

**Decisions affecting this repo:**
- 2026-03-25: Every repo in the org runs `semgrep --config semgrep-no-animal-violence.yaml` on all code/docs edits as a quality gate.
- 2026-04-01: The no-animal-violence suite is the model for how shared canonical configs should work org-wide (the external contribution safety pattern should mirror this structure).
- 2026-04-18: `rules.yaml` is the sole canonical source. All generated files in `alex/`, `woke/`, `vale/Speciesism/` are produced by `generate_all.py`. Handcrafted supplementary files removed.

## Related Repos

- [vale-no-animal-violence](https://github.com/Open-Paws/vale-no-animal-violence) — Standalone Vale distribution package
- [eslint-plugin-no-animal-violence](https://github.com/Open-Paws/eslint-plugin-no-animal-violence) — ESLint plugin for JS/TS
- [semgrep-rules-no-animal-violence](https://github.com/Open-Paws/semgrep-rules-no-animal-violence) — Semgrep rules
- [vscode-no-animal-violence](https://github.com/Open-Paws/vscode-no-animal-violence) — VS Code extension
- [no-animal-violence-action](https://github.com/Open-Paws/no-animal-violence-action) — GitHub Action
- [no-animal-violence-pre-commit](https://github.com/Open-Paws/no-animal-violence-pre-commit) — pre-commit hook
- [reviewdog-no-animal-violence](https://github.com/Open-Paws/reviewdog-no-animal-violence) — reviewdog runner
- [danger-plugin-no-animal-violence](https://github.com/Open-Paws/danger-plugin-no-animal-violence) — Danger.js plugin
- [alex-no-animal-violence](https://github.com/Open-Paws/alex-no-animal-violence) — Alex/retext-equality rules
- [woke-no-animal-violence](https://github.com/Open-Paws/woke-no-animal-violence) — Woke scanner config

## Development Standards

### 10-Point Review Checklist (ranked by AI violation frequency)

1. **DRY** — AI clones rule patterns at 4x the human rate. Search existing rules before adding new ones.
2. **Deep modules** — Each rule file covers one category cleanly. No mixed concerns (idioms + tech terms in one file).
3. **Single responsibility** — One rule entry = one pattern. Don't bundle multiple phrases into a single regex.
4. **Error handling** — Validate YAML structure; fail explicitly on malformed rule files rather than silently skipping.
5. **Information hiding** — Rule files expose patterns and alternatives, not internal implementation details of consumers.
6. **Ubiquitous language** — Use movement terminology: "farmed animal" not "livestock," "factory farm" not "farm." Never introduce synonyms for domain terms.
7. **Design for change** — Rules should be addable/removable without restructuring the file. Each consumer embeds these patterns inline — changes require downstream propagation checks.
8. **Legacy velocity** — Before modifying existing rules, verify no downstream consumer breaks. Pre-commit and CI action embed patterns inline.
9. **Over-patterning** — A flat list of patterns is better than a complex inheritance hierarchy. Keep rule files simple.
10. **Test quality** — New rules must include both a true-positive example (what gets flagged) and a false-positive suppression example (what should not get flagged).

### Quality Gates

- **Desloppify**: `desloppify scan --path .` — minimum score ≥85.
- **Self-check**: Run the rules against this repo's own documentation to catch accidental violations in comments or descriptions.
- **Two-failure rule**: After two failed fixes on the same problem, stop and restart with a better approach.

### Testing Methodology

- Spec-first: define what a new rule catches (and what it does not) before writing the YAML.
- Every rule must have at least one true-positive example and one false-positive suppression example.
- Three questions per rule: (1) Does it catch the target phrase? (2) Does it avoid flagging legitimate uses (POSIX `kill()`, `git master`, quotations, proper nouns)? (3) Is the suggested alternative genuinely better?

### Seven Concerns — Repo-Specific Notes

1. **Testing** — Rule files need example-based tests. Currently underspecified; this is a known gap.
2. **Security** — Context suppression logic (for POSIX calls, system terms) must be audited to avoid silently suppressing legitimate security-relevant patterns.
3. **Privacy** — Not applicable to this repo.
4. **Cost optimization** — Static files, no compute costs. Rule additions are free.
5. **Advocacy domain** — This is the canonical dictionary. Every term must use movement-standard language. Never introduce euphemisms for exploitation.
6. **Accessibility** — Rule suggestions must be in plain English accessible to non-native speakers.
7. **Emotional safety** — Rule descriptions should explain *why* a phrase is problematic without exposing developers to graphic content.

### Structured Coding Reference

For tool-specific AI coding instructions (Claude Code rules, Cursor MDC, Copilot, Windsurf, etc.), copy the corresponding directory from `structured-coding-with-ai` into this project root.

## MCP Integrations (live 2026-04-09)

These tools consume the rule definitions in this repo:

- **mcp-server-nav-language** — Pure regex MCP server that loads the canonical rule patterns from this repo's `woke/.woke.yaml`, `alex/`, and `vale/Speciesism/` files at startup. Exposes three tools: `check_language`, `check_file`, `list_rules`. Sub-10ms response. Used by Gary MCP hub Phase 3. The canonical pattern dictionary here is what that server enforces at runtime.
- **lbr8-mcp-constraints** — Wraps any MCP tool handler with NAV constraint middleware. `StaticConstraintSource` bundles 12 offline NAV patterns sourced from this suite.
- **mcp-server-aha-evaluation** — Uses NAV rules as Stage 1 of a two-stage content evaluation pipeline.
- **Audit-to-dispatch (decision #37, 2026-04-11)** — NAV violations found during ecosystem audits now auto-dispatch as agent fix tasks. This repo's patterns are the violation definition used by that pipeline.

## Decisions Reviewed

Last reviewed: 2026-04-18 (alex + woke promoted to downstream repos; rules.yaml made sole canonical source; handcrafted supplementary files removed)
