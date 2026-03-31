# No Animal Violence

Rule files for detecting speciesist language in code, documentation, and prose. Compatible with multiple popular inclusive language scanning tools.

## What This Is

Extensions for existing inclusive language tools that detect phrases normalizing violence toward animals and suggest clearer, more professional alternatives. Every major inclusive language scanner covers racial, gender, and ableist language — none currently include speciesism.

This project fills that gap with rule files for:

- **[woke](https://github.com/get-woke/woke)** — `.woke.yaml` config file
- **[alex / retext-equality](https://github.com/retextjs/retext-equality)** — YAML pattern file for the `data/en/` directory
- **[Vale](https://vale.sh)** — Distributable style package

## What It Detects

### Violent Animal Idioms
Phrases that normalize violence toward animals, with clearer professional alternatives:
- "kill two birds with one stone" → "accomplish two things at once"
- "beat a dead horse" → "belabor the point"
- "more than one way to skin a cat" → "more than one way to solve this"

### Animal-as-Object Metaphors
Terms that frame animals as tools, objects, or insults:
- "guinea pig" → "test subject"
- "sacred cow" → "unquestioned belief"
- "scapegoat" → "wrongly blamed"

### Technical Terminology
Infrastructure metaphors with animal exploitation origins, with more precise alternatives:
- "cattle vs. pets" → "ephemeral vs. persistent"
- "canary deployment" → "progressive rollout"
- "monkey patch" → "runtime patch"

## Academic Foundation

This work is grounded in peer-reviewed research documenting speciesist bias in language and AI systems:

- Hagendorff, Bossert, Tse & Singer (2023). "Speciesist bias in AI." *AI and Ethics*. [DOI: 10.1007/s43681-023-00380-w](https://doi.org/10.1007/s43681-023-00380-w)
- Takeshita, Rzepka & Araki (2022). "Speciesist language and nonhuman animal bias in English masked language models." *Information Processing & Management*.
- Hagendorff et al. (2025). "SpeciesismBench: A benchmark for evaluating speciesist bias in large language models." arXiv:2508.11534.
- Leach et al. (2023). "Speciesism in everyday language." *British Journal of Social Psychology*.

## Adding to Your Project

See **[INTEGRATION.md](INTEGRATION.md)** for a single guide that covers all nine tools — from a 5-minute GitHub Action setup to the full local + CI stack in 15 minutes.

## License

MIT

## About

Built by [Open Paws](https://openpaws.ai) — AI infrastructure for animal liberation.
