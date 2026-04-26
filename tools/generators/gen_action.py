#!/usr/bin/env python3
"""Generate GitHub Action action.yml from rules.yaml.

Output: build/no-animal-violence-action/action.yml
"""
from __future__ import annotations

import sys
from pathlib import Path

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
  severity:
    description: 'Minimum severity that fails CI: error | warning | info'
    required: false
    default: 'warning'
  fail-on-findings:
    description: 'Fail the workflow when patterns are found. Set false for gradual adoption.'
    required: false
    default: 'true'
  github-token:
    description: 'GitHub token for PR annotations'
    required: false
    default: ${{ github.token }}

runs:
  using: 'composite'
  steps:
"""

STATIC_FOOTER = """\
    - name: Verify Python 3
      shell: bash
      run: python3 --version

    - name: Inject canonical Open Paws paths into .wokeignore
      shell: bash
      run: |
        if ! grep -qF "# no-animal-violence-action: canonical paths" .wokeignore 2>/dev/null; then
          printf '\\n# no-animal-violence-action: canonical paths\\n' >> .wokeignore
          printf '.claude/rules/\\nCLAUDE.md\\nAGENTS.md\\n' >> .wokeignore
        fi

    - name: Scan for language that normalizes violence toward animals
      shell: bash
      env:
        INPUT_PATHS: ${{ inputs.paths }}
        INPUT_SEVERITY: ${{ inputs.severity }}
        INPUT_FAIL_ON_FINDINGS: ${{ inputs.fail-on-findings }}
      run: python3 "$GITHUB_ACTION_PATH/scan.py"
"""


def generate(rules: list[Rule], output_path: Path) -> None:
    """Write the action.yml file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = STATIC_HEADER + STATIC_FOOTER
    output_path.write_text(content, encoding="utf-8")


def main() -> int:
    rules = load_rules(canonical_rules_path())
    generate(rules, OUTPUT_PATH)
    print(f"Action: wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
