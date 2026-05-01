#!/usr/bin/env python3
"""Generate GitHub Action action.yml from rules.yaml.

Output: build/no-animal-violence-action/action.yml
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loader import Rule, canonical_rules_path, load_rules  # noqa: E402

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

# Canonical Open Paws paths emitted as woke `ignore_files` patterns (gitignore
# syntax). These files exist by design across every Open Paws repo and contain
# domain terms (personas, rule descriptions) that the scanner would otherwise
# flag on every PR. Inlining them here is plan v2 for #65 — the previous
# .wokeignore mutation step never propagated to the deployed action.yml.
CANONICAL_IGNORE_FILES = [
    "scout.personas.yaml",
    "AGENTS.md",
    "CLAUDE.md",
    "**/.claude/rules/",
]


def _build_woke_yaml(rules: list[Rule], indent: int = 8) -> str:
    """Render rules in woke YAML format, indented for heredoc embedding.

    Emits two top-level keys:
      - `ignore_files`: list of gitignore-style patterns telling woke to skip
        the canonical Open Paws files (personas fixtures, AGENTS.md, CLAUDE.md,
        .claude/rules/) at scan time. Per woke pkg/config/config.go this maps
        to `IgnoreFiles []string` — must be a list, never a single string.
      - `rules`: the rule entries woke matches against.
    """
    pad = " " * indent
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
        entry["reason"] = rule.reason
        rules_list.append(entry)
    dumped = yaml.safe_dump(
        {
            "ignore_files": list(CANONICAL_IGNORE_FILES),
            "rules": rules_list,
        },
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    return "\n".join(pad + line for line in dumped.splitlines())


def generate(rules: list[Rule], output_path: Path) -> None:
    """Write the action.yml file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    woke_content = _build_woke_yaml(rules)
    content = STATIC_HEADER + woke_content + "\n" + STATIC_FOOTER
    output_path.write_text(content, encoding="utf-8")


def main() -> int:
    rules = load_rules(canonical_rules_path())
    generate(rules, OUTPUT_PATH)
    print(f"Action: wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
