#!/usr/bin/env python3
"""Generate pre-commit hook from rules.yaml.

Output: build/no-animal-violence-pre-commit/no_animal_violence_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loader import Rule, canonical_rules_path, load_rules  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = (
    REPO_ROOT / "build" / "no-animal-violence-pre-commit" / "no_animal_violence_check.py"
)

STATIC_FOOTER = r'''
COMPILED = [(re.compile(pattern, re.IGNORECASE), alt) for pattern, alt in PATTERNS]


def check_file(filepath):
    """Check a single file for animal violence language. Returns list of findings."""
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line_num, line in enumerate(f, start=1):
                for regex, alternative in COMPILED:
                    for match in regex.finditer(line):
                        findings.append(
                            (filepath, line_num, match.group(), alternative)
                        )
    except (OSError, IOError):
        pass
    return findings


def main():
    """Entry point. Accepts filenames as arguments (provided by pre-commit)."""
    filenames = sys.argv[1:]
    if not filenames:
        return 0

    all_findings = []
    for filename in filenames:
        all_findings.extend(check_file(filename))

    if all_findings:
        print("Animal violence language detected:\n")
        for filepath, line_num, matched, alternative in all_findings:
            print(f"  {filepath}:{line_num}")
            print(f'    Found:   "{matched}"')
            print(f'    Suggest: "{alternative}"\n')
        print(
            f"{len(all_findings)} instance(s) found. "
            "Consider using the suggested alternatives."
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def generate(rules: list[Rule], output_path: Path) -> None:
    """Write the pre-commit hook Python file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pattern_lines = []
    for rule in rules:
        escaped_regex = rule.regex.replace('"', '\\"')
        if rule.word_boundary:
            escaped_regex = f'\\b(?:{escaped_regex})\\b'
        escaped_alt = rule.primary_alt.replace('"', '\\"')
        pattern_lines.append(f'    (r"{escaped_regex}", "{escaped_alt}"),')


    patterns_block = "\n".join(pattern_lines)

    header = '# AUTO-GENERATED from Open-Paws/no-animal-violence. Do not edit directly.\n'
    header += '"""Pre-commit hook for detecting language that normalizes violence toward animals."""\n\n'
    header += "import re\nimport sys\n\n\nPATTERNS = [\n"

    content = header + patterns_block + "\n]\n" + STATIC_FOOTER
    output_path.write_text(content, encoding="utf-8")


def main() -> int:
    rules = load_rules(canonical_rules_path())
    generate(rules, OUTPUT_PATH)
    print(f"Pre-commit: wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
