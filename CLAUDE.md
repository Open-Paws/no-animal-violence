# no-animal-violence

Rule files for detecting speciesist language in code, documentation, and prose. Part of the Open Paws speciesist language detection suite. Compatible with woke, alex/retext-equality, and Vale.

## Quick Start

Rules are static YAML/config files — no build step required. Copy or reference the relevant directory for your tool:

- **woke**: use `woke/.woke.yaml`
- **alex/retext-equality**: use files in `alex/`
- **Vale**: use the `vale/Speciesism/` style package

## Architecture

This is a **mono-repo of rule definitions** for three different inclusive-language scanners. Each tool has its own directory with rules in its native format. All rule sets detect the same categories: violent animal idioms, animal-as-object metaphors, and speciesist technical terminology.

## Key Files

| File | Description |
|------|-------------|
| `woke/.woke.yaml` | woke scanner config with all speciesist patterns |
| `alex/animal-violence.yml` | alex/retext-equality rules for violent idioms |
| `alex/speciesism.yml` | alex/retext-equality rules for speciesist metaphors |
| `vale/Speciesism/AnimalIdioms.yml` | Vale rule: violent animal idioms |
| `vale/Speciesism/AnimalMetaphors.yml` | Vale rule: animal-as-object metaphors |
| `vale/Speciesism/TechTerminology.yml` | Vale rule: speciesist tech terms |
| `vale/Speciesism/meta.json` | Vale style package metadata |

## Related Repos

- [vale-no-animal-violence](https://github.com/Open-Paws/vale-no-animal-violence) — Standalone Vale distribution package
- [eslint-plugin-no-animal-violence](https://github.com/Open-Paws/eslint-plugin-no-animal-violence) — ESLint plugin for JS/TS
