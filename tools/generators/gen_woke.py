#!/usr/bin/env python3
"""Generate woke config files from rules.yaml.

Outputs (downstream):
  build/woke-no-animal-violence/.woke.yaml

Outputs (canonical inline):
  woke/.woke.yaml
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loader import Rule, canonical_rules_path, load_rules  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CANONICAL_PATH = REPO_ROOT / "woke" / ".woke.yaml"
BUILD_PATH = REPO_ROOT / "build" / "woke-no-animal-violence" / ".woke.yaml"


def generate(rules: list[Rule], output_path: Path) -> None:
    """Write a woke config from rules (dropping fields woke doesn't understand)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rules_list = []
    for rule in rules:
        entry: dict = {
            "name": rule.name,
            "terms": rule.terms,
            "alternatives": rule.alternatives,
            "severity": rule.severity,
            "options": {
                "word_boundary": rule.word_boundary,
                "categories": [rule.category],
            },
        }
        if rule.note:
            entry["note"] = rule.note
        rules_list.append(entry)
    header = "# AUTO-GENERATED from rules.yaml. Do not edit directly.\n"
    header += "# Run tools/generate_all.py to regenerate.\n"
    body = yaml.safe_dump(
        {"rules": rules_list},
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    output_path.write_text(header + body, encoding="utf-8")


def main() -> int:
    rules = load_rules(canonical_rules_path())
    generate(rules, CANONICAL_PATH)
    generate(rules, BUILD_PATH)
    print(f"Woke: wrote {CANONICAL_PATH}")
    print(f"Woke: wrote {BUILD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
