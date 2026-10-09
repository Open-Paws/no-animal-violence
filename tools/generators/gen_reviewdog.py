#!/usr/bin/env python3
"""Generate reviewdog action.yml from rules.yaml.

Output: build/reviewdog-no-animal-violence/action.yml

The reviewdog action has no phrase list — it runs the stdlib-only scan.py that is
bundled in the Open-Paws/reviewdog-no-animal-violence repo (output is already in
reviewdog's "file:line: message" format). This generator writes the file
deterministically.
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
    description: 'Reporter for reviewdog (github-pr-check, github-pr-review, github-check, github-pr-annotations, local)'
    required: false
    default: 'github-pr-review'
  filter_mode:
    description: 'Filtering mode for reviewdog (added, diff_context, file, nofilter)'
    required: false
    default: 'added'

runs:
  using: 'composite'
  steps:
    # Pinned to a commit SHA so a moved tag cannot change what runs.
    - uses: reviewdog/action-setup@d8a7baabd7f3e8544ee4dbde3ee41d0011c3a93f # v1.5.0

    # Inputs are passed through env vars (never interpolated into the script)
    # and checked against an allowlist, to prevent shell injection.
    - name: Validate inputs
      shell: bash
      env:
        NAV_REPORTER: ${{ inputs.reporter }}
        NAV_LEVEL: ${{ inputs.level }}
        NAV_FILTER_MODE: ${{ inputs.filter_mode }}
      run: |
        case "$NAV_REPORTER" in
          github-pr-check|github-pr-review|github-check|github-pr-annotations|local) ;;
          *) echo "::error::Invalid reporter input"; exit 1 ;;
        esac
        case "$NAV_LEVEL" in
          info|warning|error) ;;
          *) echo "::error::Invalid level input"; exit 1 ;;
        esac
        case "$NAV_FILTER_MODE" in
          added|diff_context|file|nofilter) ;;
          *) echo "::error::Invalid filter_mode input"; exit 1 ;;
        esac

    # Uses the stdlib-only scanner bundled with this action (scan.py), so no
    # third-party package is downloaded at run time.
    - name: Run no-animal-violence check with reviewdog
      shell: bash
      env:
        REVIEWDOG_GITHUB_API_TOKEN: ${{ inputs.github_token }}
        NAV_ACTION_PATH: ${{ github.action_path }}
        NAV_REPORTER: ${{ inputs.reporter }}
        NAV_LEVEL: ${{ inputs.level }}
        NAV_FILTER_MODE: ${{ inputs.filter_mode }}
      run: |
        python3 "$NAV_ACTION_PATH/scan.py" \\
          | sed 's|^\\./||' \\
          | reviewdog -efm="%f:%l: %m" \\
              -name="no-animal-violence" \\
              -reporter="$NAV_REPORTER" \\
              -level="$NAV_LEVEL" \\
              -filter-mode="$NAV_FILTER_MODE"
"""


def main() -> int:
    load_rules(canonical_rules_path())
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(CONTENT, encoding="utf-8")
    print(f"Reviewdog: wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
