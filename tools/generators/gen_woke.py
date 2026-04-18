#!/usr/bin/env python3
"""Generate woke/.woke.yaml from rules.yaml.

Writes directly to the canonical repo's woke/.woke.yaml
(not to build/) since it lives in the same repo.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loader import Rule, canonical_rules_path, load_rules

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = REPO_ROOT / "woke" / ".woke.yaml"


def generate(rules: list[Rule], output_path: Path) -> None:
    """Write woke/.woke.yaml from rules (dropping fields woke doesn't understand)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AUTO-GENERATED from rules.yaml. Do not edit directly.\n",
        "# Run tools/generate_all.py to regenerate.\n",
        "rules:\n",
    ]
    for rule in rules:
        lines.append(f"- name: {rule.name}\n")
        lines.append("  terms:\n")
        for term in rule.terms:
            lines.append(f"  - {term}\n")
        lines.append("  alternatives:\n")
        for alt in rule.alternatives:
            lines.append(f"  - {alt}\n")
        lines.append(f"  severity: {rule.severity}\n")
        if rule.note:
            # Use quoted scalar for notes with special characters
            if any(c in rule.note for c in [':', "'", '"', '#', '{', '}', '[', ']', '\n']):
                note_safe = rule.note.replace('"', '\\"')
                lines.append(f'  note: "{note_safe}"\n')
            else:
                lines.append(f"  note: {rule.note}\n")
        lines.append("  options:\n")
        lines.append(f"    word_boundary: {'true' if rule.word_boundary else 'false'}\n")
        lines.append("    categories:\n")
        lines.append(f"    - {rule.category}\n")
    output_path.write_text("".join(lines))


def main() -> int:
    rules = load_rules(canonical_rules_path())
    generate(rules, OUTPUT_PATH)
    print(f"Woke: wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
