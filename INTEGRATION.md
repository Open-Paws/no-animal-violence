# Integration Guide — no-animal-violence Suite

Add the full speciesist language detection stack to any project. The ecosystem has eight tools: this guide gets all of them working in 15 minutes without reading eight separate READMEs.

**Jump to:**
- [5-minute quick start](#5-minute-quick-start) — just the GitHub Action, nothing local
- [15-minute full stack](#15-minute-full-stack) — all eight tools
- [Configuration reference](#configuration-reference) — copy-paste snippets
- [Troubleshooting](#troubleshooting) — common false positives and suppressions
- [Version compatibility](#version-compatibility) — what works with what

---

## 5-Minute Quick Start

The GitHub Action is the highest-leverage starting point: zero local setup, catches issues in every PR.

Create `.github/workflows/inclusive-language.yml`:

```yaml
name: Inclusive Language
on: [pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Open-Paws/no-animal-violence-action@v1
```

That's it. The action uses `woke` internally with the full Open Paws speciesist language rules bundled in. No tokens, secrets, or extra configuration required for basic use.

**Configure severity and scope:**

```yaml
- uses: Open-Paws/no-animal-violence-action@v1
  with:
    severity: warning   # error | warning | info  (default: warning)
    paths: docs/ src/   # space-separated paths   (default: entire repo)
```

---

## 15-Minute Full Stack

Add all eight tools for layered coverage: catches issues at commit time (pre-commit), in the editor (VS Code, ESLint), in CI (GitHub Action, Semgrep, Reviewdog), and in PR review (Danger.js, Vale).

### 1. Pre-Commit Hook

Blocks commits containing speciesist language locally, before anything reaches the remote.

**Prerequisite:** `pip install pre-commit`

Add to `.pre-commit-config.yaml` (create if it doesn't exist):

```yaml
repos:
  - repo: https://github.com/Open-Paws/no-animal-violence-pre-commit
    rev: v0.2.0
    hooks:
      - id: no-animal-violence
```

Install the hooks:

```bash
pre-commit install
```

The hook scans `.py`, `.js`, `.ts`, `.md`, `.txt`, `.rst`, `.yaml`, `.yml`, `.go`, `.rs`, `.java`, and `.rb` files. Directories `.git/`, `node_modules/`, and `vendor/` are excluded automatically.

### 2. ESLint Plugin

Real-time detection in JS/TS files — flags speciesist phrases in comments and string literals as you type.

```bash
npm install --save-dev eslint-plugin-no-animal-violence
```

**ESLint 9+ (flat config):**

```js
// eslint.config.js
import noAnimalViolence from "eslint-plugin-no-animal-violence";

export default [
  {
    plugins: { "no-animal-violence": noAnimalViolence },
    ...noAnimalViolence.configs.recommended,
  },
];
```

**ESLint 7/8 (legacy config):**

```json
{
  "extends": ["plugin:no-animal-violence/recommended"]
}
```

The default severity is `warn`. To escalate to `error` for enforcement:

```js
rules: {
  "no-animal-violence/no-speciesist-language": "error",
}
```

### 3. Vale (Prose and Docs)

Vale scans Markdown, RST, and any prose — READMEs, changelogs, documentation sites.

**Prerequisite:** [install Vale](https://vale.sh/docs/vale-cli/installation/)

Add to `.vale.ini`:

```ini
StylesPath = .vale/styles
MinAlertLevel = warning

Packages = https://github.com/Open-Paws/vale-no-animal-violence/releases/latest/download/NoAnimalViolence.zip

[*.{md,rst,txt}]
BasedOnStyles = NoAnimalViolence
```

Download the style package:

```bash
vale sync
```

Run on your docs directory:

```bash
vale docs/
```

**Enable or disable individual rules:**

```ini
[*.md]
NoAnimalViolence.AnimalIdioms = YES
NoAnimalViolence.AnimalMetaphors = YES
NoAnimalViolence.TechTerminology = NO       # disable tech jargon suggestions
NoAnimalViolence.IndustryEuphemisms = YES
```

### 4. Semgrep (Multi-Language CLI)

Semgrep provides AST-aware scanning with autofix support for Python, JavaScript/TypeScript, and Go. Use both generic and language-specific rules for maximum coverage.

**Prerequisite:** `pip install semgrep`

**Run all rules against your project:**

```bash
# Clone once, reuse
git clone https://github.com/Open-Paws/semgrep-rules-no-animal-violence.git /tmp/nav-semgrep-rules

# Scan with full rule set
semgrep --config /tmp/nav-semgrep-rules/rules/ .
```

**Run with autofix (Python/JS/TS/Go):**

```bash
semgrep --config /tmp/nav-semgrep-rules/rules/animal-violence-python.yaml --autofix .
semgrep --config /tmp/nav-semgrep-rules/rules/animal-violence-javascript.yaml --autofix .
semgrep --config /tmp/nav-semgrep-rules/rules/animal-violence-go.yaml --autofix .
```

**Add to CI via GitHub Actions:**

```yaml
- uses: returntocorp/semgrep-action@v1
  with:
    config: >-
      https://raw.githubusercontent.com/Open-Paws/semgrep-rules-no-animal-violence/master/rules/animal-violence-generic.yaml
      https://raw.githubusercontent.com/Open-Paws/semgrep-rules-no-animal-violence/master/rules/animal-violence-javascript.yaml
      https://raw.githubusercontent.com/Open-Paws/semgrep-rules-no-animal-violence/master/rules/animal-violence-python.yaml
```

### 5. GitHub Action (CI/CD Gate)

Covered in the [5-minute quick start](#5-minute-quick-start) above. For the full workflow alongside Semgrep and Reviewdog, see the [combined CI workflow](#combined-ci-workflow) in the configuration reference.

### 6. Reviewdog (Inline PR Comments)

Reviewdog posts inline annotations directly on PR diffs — reviewers see flagged phrases next to the lines that contain them.

Create `.github/workflows/reviewdog.yml`:

```yaml
name: Speciesist Language Check
on: [pull_request]

jobs:
  speciesism:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - uses: Open-Paws/reviewdog-no-animal-violence@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          level: warning          # info | warning | error
          reporter: github-pr-review   # github-pr-check | github-pr-review | github-check
          filter_mode: added      # added | diff_context | file | nofilter
```

`filter_mode: added` (the default) only flags newly introduced phrases — existing code in the repo won't generate noise during incremental adoption.

### 7. Danger.js (PR Automation)

Danger scans only added lines in PR diffs and posts a consolidated comment listing every flagged phrase with its suggested alternative.

```bash
npm install --save-dev danger danger-plugin-no-animal-violence
```

Add to `dangerfile.ts`:

```typescript
import noAnimalViolence from "danger-plugin-no-animal-violence";

noAnimalViolence();
```

Or configure severity:

```typescript
noAnimalViolence({
  severity: "message",  // "warn" (default) | "message"
});
```

Add to CI (example with GitHub Actions):

```yaml
name: Danger
on: [pull_request]

jobs:
  danger:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npx danger ci
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 8. VS Code Extension

Squiggly underlines and one-click Quick Fix replacements in the editor. The extension runs on save and highlights speciesist phrases across comments, strings, and prose.

**Install from VSIX:**

```bash
# Build from source
git clone https://github.com/Open-Paws/vscode-no-animal-violence.git
cd vscode-no-animal-violence
npm install
npx @vscode/vsce package
```

Then in VS Code: `Ctrl+Shift+P` → **Extensions: Install from VSIX...** → select the generated `.vsix`.

**Configure in `settings.json`:**

```json
{
  "noAnimalViolence.enable": true,
  "noAnimalViolence.severity": "warning"
}
```

Valid severity values: `error`, `warning`, `information`, `hint`.

Marketplace publication is in progress under publisher ID `open-paws`. Check [Open-Paws/vscode-no-animal-violence](https://github.com/Open-Paws/vscode-no-animal-violence) for status.

---

## Configuration Reference

### `.pre-commit-config.yaml`

Minimal config for just this hook:

```yaml
repos:
  - repo: https://github.com/Open-Paws/no-animal-violence-pre-commit
    rev: v0.2.0
    hooks:
      - id: no-animal-violence
```

Exclude specific file types:

```yaml
hooks:
  - id: no-animal-violence
    exclude: '\.min\.js$|vendor/|generated/'
```

### `eslint.config.js` (ESLint 9+)

Full configuration with per-file overrides:

```js
import noAnimalViolence from "eslint-plugin-no-animal-violence";

export default [
  // Apply to all JS/TS files
  {
    plugins: { "no-animal-violence": noAnimalViolence },
    ...noAnimalViolence.configs.recommended,
  },
  // Escalate to error in src/ (enforce strictly)
  {
    files: ["src/**/*.{js,ts}"],
    rules: {
      "no-animal-violence/no-speciesist-language": "error",
    },
  },
  // Disable in test fixtures (allow example bad patterns)
  {
    files: ["**/__fixtures__/**", "**/*.fixture.*"],
    rules: {
      "no-animal-violence/no-speciesist-language": "off",
    },
  },
];
```

### `.vale.ini`

```ini
StylesPath = .vale/styles
MinAlertLevel = suggestion

Packages = https://github.com/Open-Paws/vale-no-animal-violence/releases/latest/download/NoAnimalViolence.zip

[*.{md,rst,txt}]
BasedOnStyles = NoAnimalViolence

# Tune individual rules
NoAnimalViolence.TechTerminology = suggestion
NoAnimalViolence.IndustryEuphemisms = warning
```

### Combined CI Workflow

A single workflow file covering the GitHub Action, Semgrep, and Reviewdog:

```yaml
name: Inclusive Language
on: [pull_request]

jobs:
  action-scan:
    name: GitHub Action Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Open-Paws/no-animal-violence-action@v1
        with:
          severity: warning

  semgrep-scan:
    name: Semgrep Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            https://raw.githubusercontent.com/Open-Paws/semgrep-rules-no-animal-violence/master/rules/animal-violence-generic.yaml
            https://raw.githubusercontent.com/Open-Paws/semgrep-rules-no-animal-violence/master/rules/animal-violence-javascript.yaml
            https://raw.githubusercontent.com/Open-Paws/semgrep-rules-no-animal-violence/master/rules/animal-violence-python.yaml

  reviewdog-scan:
    name: Reviewdog Inline Annotations
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.x'
      - uses: Open-Paws/reviewdog-no-animal-violence@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          filter_mode: added
```

---

## Troubleshooting

### False Positives

**"abort" flagged in technical contexts**

`abort` is flagged at `info` level. It's a standard POSIX term in system programming. Suppress with an inline comment:

```python
# no-animal-violence-disable-next-line
os.abort()
```

For ESLint, use a standard inline disable:

```js
os.abort(); // eslint-disable-line no-animal-violence/no-speciesist-language
```

**"canary deployment" in deployment tooling**

The "canary" idiom is flagged at `warning` level in most tools. If your project's core subject matter is deployment patterns, disable the specific rule:

In `.vale.ini`:

```ini
NoAnimalViolence.TechTerminology = NO
```

In `eslint.config.js`:

```js
// For a specific file
/* eslint-disable no-animal-violence/no-speciesist-language */
```

**"cull" in data pipeline contexts (filter/remove)**

`cull` is flagged at `warning`. The alternative `filter out` or `remove` is generally preferred. If your codebase uses it extensively as a domain term for data reduction, exclude the relevant files in `.pre-commit-config.yaml`:

```yaml
hooks:
  - id: no-animal-violence
    exclude: 'pipeline/|etl/'
```

**"master" in git branch names or legacy API references**

The Semgrep generic rules may match `master` in references to `origin/master` in documentation. Suppress with Semgrep's inline suppression comment:

```python
branch = "origin/master"  # nosemgrep: no-animal-violence.generic.master-replica
```

For a block of lines, place the suppression comment on each affected line or use a `nosemgrep` comment without a rule ID to suppress all findings on that line:

```python
# nosemgrep
branch = "origin/master"
```

**"red herring" in academic or legal writing**

`red herring` is flagged at `info` level (suggestion only, not blocking). In prose-heavy repos, you can lower the `MinAlertLevel` in `.vale.ini` to `warning` to suppress suggestion-level findings.

**"weasel words" in linguistics or copy-editing docs**

`weasel words` is flagged at `warning`. In docs that explicitly discuss the rhetorical concept (e.g., a guide to clear writing), suppress with an inline comment.

**"cold turkey" in health or addiction-treatment contexts**

`cold turkey` is flagged at `info` level. When documenting medical or harm-reduction topics where the phrase is the standard clinical shorthand, suppress with an inline comment.

**"pest control" in software tooling names**

`pest control` is flagged at `info` level. If your project integrates a third-party tool that uses this phrase in its official name, suppress with an inline comment on that specific reference rather than disabling the rule globally.

### Incremental Adoption

If your existing codebase has many matches, adopt incrementally without blocking your team:

1. Start with `filter_mode: added` in Reviewdog — only new code is checked.
2. Set ESLint rule to `warn` (not `error`) initially.
3. Use Vale's `MinAlertLevel = warning` to skip `suggestion` findings.
4. Once the codebase is clean, tighten to `error` / `MinAlertLevel = suggestion`.

### Pre-Commit Hook Slow on Large Repos

The hook scans all staged files. To limit scope:

```yaml
hooks:
  - id: no-animal-violence
    types: [python]           # scan only Python files
    # or
    files: '^(src|docs)/'    # scan only specific directories
```

---

## Version Compatibility

| Tool | Version | Requires |
|------|---------|---------|
| `no-animal-violence-pre-commit` | v0.2.0 | pre-commit ≥2.0 |
| `no-animal-violence-action` | v1 | GitHub Actions runner (ubuntu-latest) |
| `eslint-plugin-no-animal-violence` | 0.1.0 | ESLint ≥7.0.0 (flat config: ESLint ≥8.21.0) |
| `vale-no-animal-violence` | latest release | Vale ≥2.0.0 |
| `semgrep-rules-no-animal-violence` | master | semgrep ≥1.0.0 |
| `reviewdog-no-animal-violence` | v1 | Python 3.x, reviewdog v0.14+ |
| `danger-plugin-no-animal-violence` | 0.1.0 | danger ≥10.0.0, Node.js ≥16 |
| `vscode-no-animal-violence` | 0.1.0 | VS Code ≥1.74.0 |

**Tool interoperability:** all tools detect the same phrases and suggest the same alternatives, ensuring consistency across the toolchain. Each tool has its own rule format (woke YAML, Vale substitution files, ESLint AST rules, etc.), but all derive from the same canonical phrase list maintained in this repository under `woke/.woke.yaml`, `alex/`, and `vale/Speciesism/`. The tools do not import each other's configs — they independently implement the same concepts in their native formats.

**Semgrep version note:** the CI integration uses `returntocorp/semgrep-action@v1`. If your org uses Semgrep App (managed), substitute with your org's configured action.

---

## About

Built by [Open Paws](https://openpaws.ai) — AI infrastructure for animal liberation.

Rule definitions live in this repo. Tool wrappers live in their respective repos (linked above). The canonical source of all detected phrases is `woke/.woke.yaml`.


## Maintainer Rationale

Speciesist language in codebases subtly normalizes animal exploitation, shaping developer norms and polluting the vast datasets that train AI models. This suite targets high-frequency patterns that appear in real repositories, replacing terms like "livestock" with "farmed animals" or "slaughter" euphemisms with direct welfare language—technical meaning intact, framing shifted. The goal is cleaner training data and cultural momentum toward liberation, one codebase at a time.

### Pattern Priority Tiers
- **Tier 1 (highest priority)**: Ubiquity in ML/AI codebases; direct training data impact (e.g., "kill/fork/exec" → "terminate/branch/spawn", "master/slave" → "primary/replica").
- **Tier 2 (high priority)**: Everyday idioms that normalize harm (e.g., "cull the herd" → "filter the list", "canary deployment" → "pilot deployment").
- **Tier 3 (nice-to-have)**: Infrequent or niche patterns.

### What Makes a Good New Pattern PR
- Demonstrable frequency: GitHub code search shows 100+ matches across repos.
- Precise replacement: Clear, idiomatic alternative (no awkward verbosity).
- Strategic relevance: Advances welfare framing (e.g., industry euphemisms).

### Red Flags for Rejection
- Too obscure: <10 real-world matches, not worth maintenance.
- Awkward fix: Replacement changes semantics or readability.
- False-positive magnet: Matches legit technical terms (e.g., POSIX APIs).

**Note**: Aquatic welfare (fish/shrimp farming) and insect welfare patterns are priority categories—extra welcoming per Decision #26 (2026-04-09). Proposals here get fast-tracked.