# no-animal-violence

**Status: 🟡 Active Development** — canonical rule source for the Open Paws speciesist language detection suite

Rule files for detecting speciesist language in code, documentation, and configuration. This is the **canonical pattern dictionary** for the entire no-animal-violence ecosystem. Eight downstream tools consume or mirror these definitions.

---

## What This Is

Every major inclusive language scanner covers racial, gender, and ableist language. None include speciesism. This repository fills that gap.

It maintains 65+ detection patterns across four categories, each with precise, professional alternatives. The patterns are published as native rule files for three scanners (`woke`, `alex/retext-equality`, `Vale`) and are mirrored by six additional tool adapters (ESLint, Semgrep, VS Code, pre-commit, GitHub Action, reviewdog, Danger.js).

**Changes made here propagate to all eight downstream tools.** This is the single source of truth.

---

## Why This Matters for Advocacy Software

Language shapes moral perception. Peer-reviewed research confirms that speciesist idioms and industry euphemisms in AI training data suppress moral concern for animals at a statistically significant level (Hagendorff et al., 2023; Takeshita et al., 2022). When those same phrases appear in developer communications, documentation, and code comments, they normalize the framing that produced the bias.

This toolchain embeds animal welfare standards into the development process itself. Every developer who installs an adapter encounters an alternative framing — and a reason for it — each time a flagged phrase appears.

**Academic backing:**
- Hagendorff, Bossert, Tse & Singer (2023). "Speciesist bias in AI." *AI and Ethics*. [DOI: 10.1007/s43681-023-00380-w](https://doi.org/10.1007/s43681-023-00380-w)
- Takeshita, Rzepka & Araki (2022). "Speciesist language and nonhuman animal bias in English masked language models." *Information Processing & Management*.
- Hagendorff et al. (2025). "SpeciesismBench: A benchmark for evaluating speciesist bias in large language models." arXiv:2508.11534.
- Leach et al. (2023). "Speciesism in everyday language." *British Journal of Social Psychology*.

---

## Pattern Categories

### 1. Violent Animal Idioms (`animal-violence`) — severity: `error` or `warning`

Phrases that reference harming, killing, or coercing animals:

| Flagged phrase | Suggested alternative |
|---|---|
| kill two birds with one stone | accomplish two things at once |
| beat a dead horse | belabor the point |
| more than one way to skin a cat | more than one way to solve this |
| like shooting fish in a barrel | trivially easy |
| like lambs to the slaughter | without resistance |
| curiosity killed the cat | curiosity led to trouble |
| like a chicken with its head cut off | in a panic |
| your goose is cooked | you're in trouble |
| throw someone to the wolves | abandon to criticism |
| bring home the bacon | bring home the results |
| flog a dead horse | belabor the point |
| no room to swing a cat | very cramped |
| clip someone's wings | restrict someone's freedom |
| open season | free-for-all |
| sacrificial lamb | expendable person |
| sitting duck | easy target |

### 2. Animal-as-Object Metaphors (`animal-violence`) — severity: `warning` or `info`

Phrases that frame animals as commodities, insults, or props:

| Flagged phrase | Suggested alternative |
|---|---|
| guinea pig | test subject |
| sacred cow | unquestioned belief |
| scapegoat | blame target |
| cash cow | profit center |
| dead cat bounce | temporary rebound |
| code monkey | developer |
| cattle vs. pets | ephemeral vs. persistent |
| herding cats | coordinating independent contributors |
| pet project | side project |
| rat race | daily grind |
| dog-eat-dog | ruthlessly competitive |
| whack-a-mole | recurring problem |

### 3. Speciesist Technical Terminology (`speciesism`) — severity: `warning` or `info`

Infrastructure and development metaphors with animal exploitation origins, where a more precise technical term exists:

| Flagged phrase | Suggested alternative |
|---|---|
| canary deployment / canary release | progressive rollout |
| monkey patch / monkey patching | runtime patch |
| duck typing | structural typing |
| dogfooding / eat your own dogfood | self-hosting |
| stack canary / canary value | sentinel value |
| rubber duck debugging | talk-through debugging |
| wolf in sheep's clothing | deceptive actor |
| weasel words | deliberately vague language |
| fox guarding the henhouse | conflicted oversight |
| horse trading | transactional negotiation |
| cold turkey | abrupt cessation |

### 4. Industry Euphemisms (`industry-euphemism`) — severity: `warning`

Agricultural and food-industry language that obscures what is actually happening to animals. These terms are disproportionately represented in AI training data at ratios of 13:1 to 34:1 over accurate alternatives:

| Flagged phrase | Suggested alternative | Ratio in training data |
|---|---|---|
| processing plant / processing facility | slaughterhouse | 34.3:1 |
| livestock | farmed animals | 24.8:1 |
| poultry | farmed birds | 16.5:1 |
| gestation crate | pregnancy cage | 15.0:1 |
| depopulation | mass killing | 13.9:1 |
| humane slaughter | slaughter | — |
| farrowing crate | birthing cage | — |
| battery cage | small wire cage | — |
| spent hen | discarded hen | — |
| broiler | chicken raised for meat | — |
| harvesting animals | killing animals | — |
| free-range eggs | eggs from hens with outdoor access | — |
| cage-free eggs | eggs from uncaged hens | — |

---

## Downstream Tool Ecosystem

All eight adapters detect the same phrases and suggest the same alternatives. Each implements the patterns in its tool's native format. The canonical source is this repository.

| Tool | Repository | What it covers |
|---|---|---|
| ESLint plugin | [eslint-plugin-no-animal-violence](https://github.com/Open-Paws/eslint-plugin-no-animal-violence) | JS/TS files: comments, strings, JSX |
| Semgrep rules | [semgrep-rules-no-animal-violence](https://github.com/Open-Paws/semgrep-rules-no-animal-violence) | Multi-language static analysis with autofix |
| Vale package | [vale-no-animal-violence](https://github.com/Open-Paws/vale-no-animal-violence) | Markdown, RST, prose documentation |
| VS Code extension | [vscode-no-animal-violence](https://github.com/Open-Paws/vscode-no-animal-violence) | Real-time editor underlining + Quick Fix |
| Pre-commit hook | [no-animal-violence-pre-commit](https://github.com/Open-Paws/no-animal-violence-pre-commit) | Blocks commits containing violations |
| GitHub Action | [no-animal-violence-action](https://github.com/Open-Paws/no-animal-violence-action) | CI/CD gate on every PR |
| Reviewdog runner | [reviewdog-no-animal-violence](https://github.com/Open-Paws/reviewdog-no-animal-violence) | Inline annotations on PR diffs |
| Danger.js plugin | [danger-plugin-no-animal-violence](https://github.com/Open-Paws/danger-plugin-no-animal-violence) | Consolidated PR review comment |

For full setup instructions for all eight tools, see **[INTEGRATION.md](INTEGRATION.md)**.

---

## Quick Start

**5-minute CI gate** — add to `.github/workflows/inclusive-language.yml`:

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

**Pre-commit hook** — add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Open-Paws/no-animal-violence-pre-commit
    rev: v0.2.0
    hooks:
      - id: no-animal-violence
```

**ESLint (flat config)**:

```bash
npm install --save-dev eslint-plugin-no-animal-violence
```

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

**woke** — copy or reference `woke/.woke.yaml` directly:

```bash
woke --config path/to/woke/.woke.yaml .
```

---

## How to Add a New Pattern

Patterns are governed by the same principles as code: clarity over cleverness, single responsibility per entry, and every new rule must include at least one true-positive example and one false-positive suppression example.

### Governance process

1. **Check for duplicates first.** Search `woke/.woke.yaml`, `alex/animal-violence.yml`, `alex/speciesism.yml`, `alex/industry-euphemisms.yml`, and `vale/Speciesism/` before adding anything. AI-assisted additions duplicate at a significantly higher rate than human-authored ones.

2. **Classify the category.** Determine which of the four categories applies: `animal-violence` (idioms or insults), `speciesism` (normalized metaphors), `industry-euphemism` (agricultural euphemisms), or a new category if none fits.

3. **Write a spec first.** Before writing the YAML, define:
   - The exact phrase(s) to flag
   - The suggested alternative(s)
   - One true-positive example (a sentence that should trigger the rule)
   - One false-positive example (a sentence that should not trigger the rule)

4. **Add to all three canonical files:**
   - `woke/.woke.yaml` — woke format
   - `alex/` — the appropriate alex/retext-equality file
   - `vale/Speciesism/` — the appropriate Vale rule file

5. **Open issues in downstream tool repos** to pull the new pattern in. See `VERSIONS.md` for the full list of downstream repos.

6. **Validate:**
   ```bash
   # Check cross-file consistency
   python tools/check_consistency.py

   # Run the suite against itself
   woke --config woke/.woke.yaml .
   ```

### Severity guidelines

| Severity | Use when |
|---|---|
| `error` | Phrase directly references animal harm with no legitimate technical use |
| `warning` | Phrase normalizes exploitation; technical contexts may exist |
| `info` | Common idiom; flag for awareness only; not blocking |

---

## Contributing

1. Read the existing patterns before proposing additions — search broadly.
2. Follow the governance process above.
3. Run `python tools/check_consistency.py` before opening a PR.
4. Every PR must include true-positive and false-positive examples for each new rule.
5. PRs that modify existing rule IDs or remove patterns are high-risk and require explicit justification — downstream tool suppression comments reference rule IDs by name.

---

## Repository Structure

```
no-animal-violence/
├── woke/
│   └── .woke.yaml              # Canonical pattern dictionary (all 65+ rules)
├── alex/
│   ├── animal-violence.yml     # Violent idioms + industry euphemisms (alex format)
│   ├── speciesism.yml          # Speciesist metaphors + tech terminology (alex format)
│   └── industry-euphemisms.yml # Harvest/welfare-washing euphemisms (alex format)
├── vale/
│   └── Speciesism/
│       ├── AnimalIdioms.yml    # Vale: violent animal idioms
│       ├── AnimalMetaphors.yml # Vale: animal-as-object metaphors
│       ├── TechTerminology.yml # Vale: speciesist tech terms
│       ├── IndustryEuphemisms.yml # Vale: agricultural euphemisms
│       └── meta.json           # Vale style package metadata
├── tools/
│   └── check_consistency.py   # Cross-file consistency validator
├── scripts/
│   └── check_versions.sh      # Downstream version drift detector
├── semgrep-no-animal-violence.yaml  # Semgrep import shim
├── INTEGRATION.md              # Full setup guide for all eight tools
└── VERSIONS.md                 # Compatibility matrix for downstream tools
```

---

## License

MIT

---

## About

Built by [Open Paws](https://openpaws.ai) — AI infrastructure for animal liberation.
