# AGENTS.md — no-animal-violence

This repository is the **canonical rule dictionary** for the Open Paws speciesist language detection suite. It contains 65+ detection patterns across four categories (violent animal idioms, animal-as-object metaphors, speciesist tech terminology, and industry euphemisms), each with precise alternatives backed by peer-reviewed research. Eight downstream tool adapters — ESLint, Semgrep, Vale, VS Code extension, pre-commit hook, GitHub Action, reviewdog runner, and Danger.js plugin — consume or mirror these definitions. A change to a rule here propagates to all eight adapters and to any MCP servers that load the patterns at runtime.

---

## Status

**Active Development** — the rule set is in use org-wide (decision 2026-03-25: all Open Paws repos run `semgrep --config semgrep-no-animal-violence.yaml` on every code/docs edit). No named maintainer as of 2026-04-02. Rule additions are welcomed; rule removals or ID changes are high-risk.

---

## Key Files

| File | Description |
|---|---|
| `woke/.woke.yaml` | The primary canonical source. All 65+ rules in woke format. Auto-generated from `project-compassionate-code` — do not edit manually. |
| `alex/animal-violence.yml` | Violent idioms and industry euphemisms in retext-equality/alex format. |
| `alex/speciesism.yml` | Speciesist metaphors and tech terminology in retext-equality/alex format. Includes true/false positive examples per rule. |
| `alex/industry-euphemisms.yml` | Harvest, free-range, and cage-free welfare-washing euphemisms in alex format. |
| `vale/Speciesism/AnimalIdioms.yml` | Vale substitution rules: violent animal idioms. |
| `vale/Speciesism/AnimalMetaphors.yml` | Vale substitution rules: animal-as-object metaphors. |
| `vale/Speciesism/TechTerminology.yml` | Vale substitution rules: speciesist tech terms (canary, monkey patch, duck typing, etc.). |
| `vale/Speciesism/IndustryEuphemisms.yml` | Vale substitution rules: agricultural euphemisms. |
| `vale/Speciesism/meta.json` | Vale style package metadata (name, version, description). |
| `semgrep-no-animal-violence.yaml` | Semgrep import shim — points to `semgrep-rules-no-animal-violence`. Not a rule file itself. |
| `tools/check_consistency.py` | Validates that all three canonical formats (woke, alex, vale) cover the same patterns. Run before every PR. |
| `scripts/check_versions.sh` | Checks installed versions of all eight downstream tools against the compatibility matrix in `VERSIONS.md`. |
| `INTEGRATION.md` | Step-by-step setup guide for all eight downstream tools. |
| `VERSIONS.md` | Compatibility matrix. Tracks which downstream tool version works with which core rule version. |

---

## Pattern Format

### woke (`.woke.yaml`)

Each rule is a YAML object with these fields:

```yaml
- name: rule-id-kebab-case          # unique, stable — downstream suppression comments reference this
  terms:                            # exact phrases to flag (case-insensitive by default)
    - the exact phrase
    - variant phrasing
  alternatives:                     # suggested replacements
    - preferred phrasing
  severity: error | warning | info  # error = blocking; warning = surfaced; info = awareness only
  note: Human-readable explanation  # why the phrase is problematic
  options:
    word_boundary: true | false     # true: flag only as whole words; false: match substrings
    categories:
      - animal-violence | industry-euphemism
```

### alex / retext-equality (`.yml` in `alex/`)

```yaml
- type: basic
  note: Explanation of why the phrase is problematic
  source: https://doi.org/...       # optional academic citation
  considerate:
    preferred phrase: a             # 'a' is the retext-equality marker for gender-neutral
  inconsiderate:
    flagged phrase: category-name   # category: animal-violence | industry-euphemism | speciesism
```

The `alex/speciesism.yml` file also includes inline comment examples for true-positive and false-positive cases:

```yaml
  # true-positive:  "Sentence that should trigger this rule."
  # false-positive: "Sentence that should NOT trigger this rule."
```

### Vale (`vale/Speciesism/*.yml`)

Vale rules use the `substitution` extension:

```yaml
extends: substitution
message: "Consider '%s' instead of '%s'."
level: suggestion | warning | error
ignorecase: true
swap:
  'flagged phrase': preferred alternative
  'flagged variant': preferred alternative
```

---

## How to Add a New Pattern Correctly

Follow all steps in order. Skipping steps leaves the rule set inconsistent across tools.

1. **Search before writing.** Run:
   ```bash
   grep -ri "your phrase" woke/ alex/ vale/
   ```
   If the phrase already exists, do not add a duplicate.

2. **Classify the category:**
   - `animal-violence` — direct harm idioms, animal-as-insult, animal exploitation metaphors
   - `industry-euphemism` — agricultural/food industry language that obscures animal harm
   - `speciesism` — normalized metaphors with precise technical alternatives

3. **Write the spec first.** Define before writing YAML:
   - Exact phrase(s) to flag
   - Suggested alternative(s)
   - One true-positive sentence (should trigger)
   - One false-positive sentence (should not trigger)

4. **Add to all three canonical file sets:**

   a. `woke/.woke.yaml` — add a new rule object. Note: this file says "AUTO-GENERATED" at the top but is the canonical source; add rules here and propagate manually.

   b. `alex/` — add to the appropriate file:
      - Violent idioms → `alex/animal-violence.yml`
      - Speciesist metaphors / tech terms → `alex/speciesism.yml`
      - Agricultural euphemisms → `alex/industry-euphemisms.yml`

   c. `vale/Speciesism/` — add to the appropriate file:
      - Violent idioms → `AnimalIdioms.yml`
      - Animal metaphors → `AnimalMetaphors.yml`
      - Tech terminology → `TechTerminology.yml`
      - Industry euphemisms → `IndustryEuphemisms.yml`

5. **Validate consistency:**
   ```bash
   python tools/check_consistency.py
   ```

6. **Open issues in downstream repos** listed in `VERSIONS.md` to pull the new pattern in. Downstream tools do not auto-sync.

---

## Integration Points (Downstream Repos)

All of these repos consume patterns from this repository:

| Repo | How it consumes these rules |
|---|---|
| [eslint-plugin-no-animal-violence](https://github.com/Open-Paws/eslint-plugin-no-animal-violence) | Embeds patterns inline from `woke/.woke.yaml` and `alex/` |
| [semgrep-rules-no-animal-violence](https://github.com/Open-Paws/semgrep-rules-no-animal-violence) | Mirrors patterns as Semgrep YAML rules |
| [vale-no-animal-violence](https://github.com/Open-Paws/vale-no-animal-violence) | Packages `vale/Speciesism/` as a distributable Vale style |
| [vscode-no-animal-violence](https://github.com/Open-Paws/vscode-no-animal-violence) | Embeds patterns for real-time editor diagnostics |
| [no-animal-violence-pre-commit](https://github.com/Open-Paws/no-animal-violence-pre-commit) | Wraps `woke` with these rules as a pre-commit hook |
| [no-animal-violence-action](https://github.com/Open-Paws/no-animal-violence-action) | Bundles rules into a GitHub Actions CI gate |
| [reviewdog-no-animal-violence](https://github.com/Open-Paws/reviewdog-no-animal-violence) | Posts inline PR annotations using these patterns |
| [danger-plugin-no-animal-violence](https://github.com/Open-Paws/danger-plugin-no-animal-violence) | Posts consolidated PR review comment |

**MCP ecosystem (live 2026-04-09):**

| Server | How it uses these rules |
|---|---|
| `mcp-server-nav-language` | Loads patterns from `woke/.woke.yaml`, `alex/`, and `vale/Speciesism/` at startup. Exposes `check_language`, `check_file`, `list_rules` tools. |
| `lbr8-mcp-constraints` | Bundles 12 offline NAV patterns as `StaticConstraintSource` for air-gapped contexts. |
| `mcp-server-aha-evaluation` | Uses NAV rules as Stage 1 of a two-stage content evaluation pipeline. |

When updating patterns here, also check whether `lbr8-mcp-constraints` (12 bundled offline patterns) needs updating.

---

## Safe vs. Risky Changes

### Low risk (proceed normally)

- Adding a new rule entry to all three canonical file sets
- Adding new alternative suggestions to an existing rule
- Improving a rule's `note` or `source` field
- Adding true-positive / false-positive examples

### High risk (require explicit justification and downstream coordination)

- **Changing a rule ID** (`name:` field in woke, rule key in alex/vale) — downstream suppression comments reference IDs by name (e.g., `# no-animal-violence-disable-next-line kill-two-birds-with-one-stone`). Changing IDs silently breaks all existing suppressions.
- **Removing an existing rule** — same risk as ID changes plus behavioural regression.
- **Changing severity downward** (e.g., `error` to `info`) — may cause violations to be silently missed in CI pipelines with minimum-severity filters.
- **Modifying the phrase list for an existing rule** — may introduce false negatives if downstream tools have cached the previous list.

For any high-risk change: (1) open an issue describing the change and its justification, (2) check all eight downstream repos for inline suppression comments that reference the affected rule ID, (3) coordinate the change across repos before merging.

---

## Known Issues / TODOs

- **No named maintainer** as of 2026-04-02. Rule additions and false-positive tuning are ideal contributions.
- **Example-based tests are underspecified.** `tools/check_consistency.py` validates cross-file consistency but does not run the rules against example sentences. A proper test fixture (true/false positive examples per rule) would close this gap.
- **Adoption metrics not tracked.** npm downloads, VS Code marketplace installs, and GitHub Action usage are not yet measured — a Lever 3 measurement gap.
- **Downstream tools do not auto-sync.** New rules added here require manual issues in each downstream repo.
- **Platform CI integration pending.** The suite has no presence in the Open Paws platform CI pipeline despite being a shipped product. See `ecosystem/integration-todos.md §27a` in the strategy repo.
- **woke/.woke.yaml header says "AUTO-GENERATED"** — this file is the canonical source and is edited directly. The header is misleading. The auto-generation pipeline in `project-compassionate-code` generates initial rule drafts; final rules are committed here.

---

## Quality Gates

```bash
# Consistency check (run before every PR)
python tools/check_consistency.py

# Self-check (run the rules against this repo's own docs)
woke --config woke/.woke.yaml .

# Downstream version drift
./scripts/check_versions.sh

# Desloppify (minimum score: 85)
desloppify scan --path .
```
