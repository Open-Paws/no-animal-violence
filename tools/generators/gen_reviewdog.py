#!/usr/bin/env python3
"""Generate reviewdog action.yml from rules.yaml.

Output: build/reviewdog-no-animal-violence/action.yml

The reviewdog action has no phrase list — it delegates to the pre-commit checker.
This generator writes the file deterministically.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loader import canonical_rules_path, load_rules  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = REPO_ROOT / "build" / "reviewdog-no-animal-violence" / "action.yml"

CONTENT = """\
# AUTO-GENERATED from Open-Paws/no-animal-violence. Do not edit directly.
name: 'Speciesist Language Scanner (reviewdog)'
description: 'Run speciesist language checks and report results via reviewdog'
author: 'Open Paws'
branding:
  icon: 'heart'
  color: 'green'

inputs:
  github_token:
    description: 'GITHUB_TOKEN'
    required: true
    default: ${{ github.token }}
  level:
    description: 'Report level for reviewdog (info, warning, error)'
    required: false
    default: 'warning'
  reporter:
    description: 'Reporter for reviewdog (github-pr-check, github-pr-review, github-check)'
    required: false
    default: 'github-pr-review'
  filter_mode:
    description: 'Filtering mode for reviewdog (added, diff_context, file, nofilter)'
    required: false
    default: 'added'

runs:
  using: 'composite'
  steps:
    - uses: reviewdog/action-setup@v1

    - name: Install no-animal-violence checker
      shell: bash
      run: pip install https://github.com/Open-Paws/no-animal-violence-pre-commit/archive/refs/tags/v0.2.0.tar.gz

    - name: Run no-animal-violence check with reviewdog
      shell: bash
      env:
        REVIEWDOG_GITHUB_API_TOKEN: ${{ inputs.github_token }}
      run: |
        find . -type f \\
          \\( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.md" \\
             -o -name "*.txt" -o -name "*.rst" -o -name "*.yaml" -o -name "*.yml" \\
             -o -name "*.go" -o -name "*.rs" -o -name "*.java" -o -name "*.rb" \\) \\
          -not -path "./.git/*" \\
          -not -path "./node_modules/*" \\
          -not -path "./vendor/*" \\
          -exec no-animal-violence-check {} + 2>&1 \\
          | python3 -c "
        import sys, re
        file_re = re.compile(r'^\\s{2}(\\S.*):(\\d+)$')
        found_re = re.compile(r'^\\s{4}Found:\\s+\\\"(.+)\\\"$')
        cur_loc = None
        for line in sys.stdin:
            line = line.rstrip()
            m = file_re.match(line)
            if m:
                cur_loc = (m.group(1), m.group(2))
                continue
            m = found_re.match(line)
            if m and cur_loc:
                print(f'{cur_loc[0]}:{cur_loc[1]}: {m.group(1)}')
                cur_loc = None
        " \\
          | reviewdog -efm="%f:%l: %m" \\
              -name="no-animal-violence" \\
              -reporter=${{ inputs.reporter }} \\
              -level=${{ inputs.level }} \\
              -filter-mode=${{ inputs.filter_mode }}
"""


def main() -> int:
    load_rules(canonical_rules_path())
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(CONTENT, encoding="utf-8")
    print(f"Reviewdog: wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
