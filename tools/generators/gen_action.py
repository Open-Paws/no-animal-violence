#!/usr/bin/env python3
"""Generate GitHub Action action.yml from rules.yaml.

Output: build/no-animal-violence-action/action.yml
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loader import Rule, canonical_rules_path, load_rules

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = REPO_ROOT / "build" / "no-animal-violence-action" / "action.yml"

STATIC_HEADER = """\
# AUTO-GENERATED from Open-Paws/no-animal-violence. Do not edit directly.
name: 'Animal Violence Language Scanner'
description: 'Scan PRs and documentation for language that normalizes violence toward animals and suggest alternatives'
author: 'Open Paws'
branding:
  icon: 'heart'
  color: 'green'

inputs:
  severity:
    description: 'Minimum severity to report (error, warning, info)'
    required: false
    default: 'warning'
  paths:
    description: 'Paths to scan (space-separated)'
    required: false
    default: '.'
  github-token:
    description: 'GitHub token for PR annotations'
    required: false
    default: ${{ github.token }}

runs:
  using: 'composite'
  steps:
    - name: Install woke
      shell: bash
      run: |
        curl -sSfL https://git.io/getwoke | bash -s -- -b /usr/local/bin

    - name: Create animal violence language rules
      shell: bash
      run: |
        cat > /tmp/.woke.yaml << 'RULES'
"""

STATIC_FOOTER = """\
        RULES

    - name: Run animal violence language scan
      shell: bash
      run: |
        woke --exit-1-on-failure \\
          --config /tmp/.woke.yaml \\
          ${{ inputs.paths }}
"""


def _build_woke_yaml(rules: list[Rule], indent: int = 8) -> str:
    """Render rules in woke YAML format, indented for heredoc embedding."""
    pad = " " * indent
    lines = [f"{pad}rules:"]
    for rule in rules:
        lines.append(f"{pad}- name: {rule.name}")
        lines.append(f"{pad}  terms:")
        for term in rule.terms:
            lines.append(f"{pad}  - {term}")
        lines.append(f"{pad}  alternatives:")
        for alt in rule.alternatives:
            lines.append(f"{pad}  - {alt}")
        lines.append(f"{pad}  severity: {rule.severity}")
        if rule.note:
            # Safe single-line quoting for notes
            note_safe = rule.note.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{pad}  note: "{note_safe}"')
        lines.append(f"{pad}  options:")
        lines.append(f"{pad}    word_boundary: {'true' if rule.word_boundary else 'false'}")
        lines.append(f"{pad}    categories:")
        lines.append(f"{pad}    - {rule.category}")
    return "\n".join(lines)


def generate(rules: list[Rule], output_path: Path) -> None:
    """Write the action.yml file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    woke_content = _build_woke_yaml(rules)
    content = STATIC_HEADER + woke_content + "\n" + STATIC_FOOTER
    output_path.write_text(content)


def main() -> int:
    rules = load_rules(canonical_rules_path())
    generate(rules, OUTPUT_PATH)
    print(f"Action: wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
