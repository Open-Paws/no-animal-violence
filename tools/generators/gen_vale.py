#!/usr/bin/env python3
"""Generate Vale rule files from rules.yaml.

Outputs (downstream):
  build/vale-no-animal-violence/NoAnimalViolence/AnimalIdioms.yml
  build/vale-no-animal-violence/NoAnimalViolence/meta.json

Outputs (canonical inline):
  vale/Speciesism/AnimalIdioms.yml
  vale/Speciesism/IndustryEuphemisms.yml
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loader import Rule, canonical_rules_path, load_rules  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUILD_DIR = REPO_ROOT / "build" / "vale-no-animal-violence" / "NoAnimalViolence"

AUTOGEN_HEADER = "# AUTO-GENERATED from Open-Paws/no-animal-violence. Do not edit directly.\n"
REFERENCE_URL = "https://doi.org/10.1007/s43681-023-00380-w"


def _build_swap(rules: list[Rule]) -> dict[str, str]:
    """Build a flat swap map: each term -> first alternative."""
    swap: dict[str, str] = {}
    for rule in rules:
        for term in rule.terms:
            if term in swap:
                print(f"Warning: duplicate term '{term}' in rule '{rule.name}', overwriting")
            swap[term] = rule.primary_alt
    return swap


def _write_vale_file(rules: list[Rule], output_path: Path, level: str = "warning") -> None:
    """Write a Vale substitution YAML file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    swap = _build_swap(rules)
    lines = [
        AUTOGEN_HEADER,
        "extends: substitution\n",
        "message: \"Consider using '%s' instead of '%s'. This phrase normalizes violence toward animals.\"\n",
        f"link: {REFERENCE_URL}\n",
        f"level: {level}\n",
        "ignorecase: true\n",
        "swap:\n",
    ]
    for term, alt in swap.items():
        term_escaped = term.replace("'", "''")
        alt_escaped = alt.replace("'", "''")
        lines.append(f"  '{term_escaped}': '{alt_escaped}'\n")
    output_path.write_text("".join(lines), encoding="utf-8")


def generate_downstream(rules: list[Rule], output_path: Path) -> None:
    """Generate the downstream vale-no-animal-violence AnimalIdioms.yml (all rules)."""
    _write_vale_file(rules, output_path)


def main() -> int:
    rules = load_rules(canonical_rules_path())

    generate_downstream(rules, BUILD_DIR / "AnimalIdioms.yml")

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "description": "Detects language that normalizes violence toward animals.",
        "url": "https://github.com/Open-Paws/vale-no-animal-violence",
    }
    (BUILD_DIR / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    animal_violence = [r for r in rules if r.category == "animal-violence"]
    industry_euphemism = [r for r in rules if r.category == "industry-euphemism"]

    canonical_vale_dir = REPO_ROOT / "vale" / "Speciesism"
    canonical_vale_dir.mkdir(parents=True, exist_ok=True)
    _write_vale_file(animal_violence, canonical_vale_dir / "AnimalIdioms.yml")
    _write_vale_file(industry_euphemism, canonical_vale_dir / "IndustryEuphemisms.yml")

    print(f"Vale: wrote downstream files to {BUILD_DIR}")
    print(f"Vale: wrote canonical files to {canonical_vale_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
