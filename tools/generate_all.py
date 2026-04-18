#!/usr/bin/env python3
"""Generate all downstream format files from rules.yaml.

Outputs go to build/<downstream-repo-name>/<path>.
Run from the repo root.
"""
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    generators = [
        ("tools/generators/gen_semgrep.py", "Semgrep"),
        ("tools/generators/gen_vale.py", "Vale"),
        ("tools/generators/gen_pre_commit.py", "Pre-commit"),
        ("tools/generators/gen_action.py", "GitHub Action"),
        ("tools/generators/gen_reviewdog.py", "Reviewdog"),
        ("tools/generators/gen_woke.py", "Woke"),
    ]
    js_generators = [
        ("tools/generators/gen_eslint.js", "ESLint"),
        ("tools/generators/gen_danger.js", "Danger"),
        ("tools/generators/gen_vscode.js", "VS Code"),
    ]

    failed = []

    for script, label in generators:
        result = subprocess.run(
            [sys.executable, repo_root / script],
            cwd=repo_root,
        )
        if result.returncode != 0:
            failed.append(label)
            print(f"FAIL: {label}")
        else:
            print(f"OK:   {label}")

    for script, label in js_generators:
        result = subprocess.run(
            ["node", repo_root / script],
            cwd=repo_root,
        )
        if result.returncode != 0:
            failed.append(label)
            print(f"FAIL: {label}")
        else:
            print(f"OK:   {label}")

    if failed:
        print(f"\nFailed: {', '.join(failed)}")
        return 1
    print("\nAll generators completed successfully.")
    print(f"Output in: {repo_root / 'build'}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
