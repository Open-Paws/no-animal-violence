#!/usr/bin/env python3
"""Generate alex/retext-equality rule files from rules.yaml.

Outputs (downstream):
  build/alex-no-animal-violence/animal-violence.yml
  build/alex-no-animal-violence/industry-euphemisms.yml

Outputs (canonical inline):
  alex/animal-violence.yml
  alex/industry-euphemisms.yml
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loader import Rule, canonical_rules_path, load_rules  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUILD_DIR = REPO_ROOT / "build" / "alex-no-animal-violence"
CANONICAL_DIR = REPO_ROOT / "alex"

AUTOGEN_HEADER = "# AUTO-GENERATED from Open-Paws/no-animal-violence. Do not edit directly.\n"
REFERENCE_URL = "https://doi.org/10.1007/s43681-023-00380-w"

CATEGORY_FILES: dict[str, str] = {
    "animal-violence": "animal-violence.yml",
    "industry-euphemism": "industry-euphemisms.yml",
}


def _write_alex_file(rules: list[Rule], output_path: Path, category: str) -> None:
    """Write an alex YAML rule file for a given category."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    for rule in rules:
        entries.append({
            "type": "basic",
            "note": rule.reason,
            "considerate": {alt: "a" for alt in rule.alternatives},
            "inconsiderate": {term: category for term in rule.terms},
            "source": REFERENCE_URL,
        })
    header = AUTOGEN_HEADER + f"# Source: {REFERENCE_URL}\n\n"
    body = yaml.safe_dump(entries, default_flow_style=False, sort_keys=False, allow_unicode=True)
    output_path.write_text(header + body, encoding="utf-8")


def main() -> int:
    rules = load_rules(canonical_rules_path())

    for category, filename in CATEGORY_FILES.items():
        category_rules = [r for r in rules if r.category == category]
        _write_alex_file(category_rules, BUILD_DIR / filename, category)
        _write_alex_file(category_rules, CANONICAL_DIR / filename, category)

    print(f"Alex: wrote downstream files to {BUILD_DIR}")
    print(f"Alex: wrote canonical files to {CANONICAL_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
