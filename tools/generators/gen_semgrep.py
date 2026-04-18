#!/usr/bin/env python3
"""Generate Semgrep rule files from rules.yaml.

Outputs:
  build/semgrep-rules-no-animal-violence/rules/animal-violence-generic.yaml
  build/semgrep-rules-no-animal-violence/rules/animal-violence-python.yaml
  build/semgrep-rules-no-animal-violence/rules/animal-violence-javascript.yaml
  build/semgrep-rules-no-animal-violence/rules/animal-violence-go.yaml
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from loader import Rule, canonical_rules_path, load_rules  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BUILD_DIR = REPO_ROOT / "build" / "semgrep-rules-no-animal-violence" / "rules"

AUTOGEN_HEADER = "# AUTO-GENERATED from Open-Paws/no-animal-violence. Do not edit directly.\n"
REFERENCE_URL = "https://doi.org/10.1007/s43681-023-00380-w"


def _alts_str(rule: Rule) -> str:
    return ", ".join(f'"{a}"' for a in rule.alternatives)


def _autofix_note(rule: Rule) -> str:
    if rule.severity in ("error", "warning"):
        return " (autofix available)."
    return "."


def _safe_yaml_single_quoted(s: str) -> str:
    """Escape a string for embedding in a YAML single-quoted scalar."""
    return s.replace("'", "''")


def generate_generic(rules: list[Rule], output_path: Path) -> None:
    """Generate the generic (regex-based) semgrep rules file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        AUTOGEN_HEADER,
        "# Generic (regex-based) rules — matches across all file types including comments\n",
        "rules:\n",
    ]
    for rule in rules:
        alts = _alts_str(rule)
        autofix = _autofix_note(rule)
        msg = f'Animal violence language: "{rule.primary_term}". Consider: {alts}{autofix}'
        lines.append(f"- id: animal-violence.{rule.name}\n")
        lines.append(f"  pattern-regex: {rule.regex}\n")
        lines.append(f"  message: '{_safe_yaml_single_quoted(msg)}'\n")
        lines.append("  languages:\n")
        lines.append("  - generic\n")
        lines.append(f"  severity: {rule.semgrep_severity}\n")
        lines.append("  metadata:\n")
        lines.append("    category: inclusive-language\n")
        lines.append(f"    subcategory: {rule.category}\n")
        lines.append(f"    alternative: {rule.primary_alt}\n")
        lines.append("    references:\n")
        lines.append(f"    - {REFERENCE_URL}\n")
    output_path.write_text("".join(lines))


def _generate_lang_file(
    rules: list[Rule],
    output_path: Path,
    lang_name: str,
    rule_id_prefix: str,
    languages: list[str],
) -> None:
    """Generate a language-specific semgrep rules file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        AUTOGEN_HEADER,
        f"# {lang_name}-specific string rules\n",
        "rules:\n",
    ]
    lang_yaml = "\n".join(f"  - {lang}" for lang in languages)
    for rule in rules:
        alts = _alts_str(rule)
        autofix = _autofix_note(rule)
        msg = (
            f'Animal violence language in string: "{rule.primary_term}". '
            f"Consider: {alts}{autofix}"
        )
        lines.append(f"- id: {rule_id_prefix}.{rule.name}\n")
        lines.append("  patterns:\n")
        lines.append("  - pattern: $S\n")
        lines.append("  - metavariable-regex:\n")
        lines.append("      metavariable: $S\n")
        lines.append(f"      regex: .*{rule.regex}.*\n")
        lines.append(f"  message: '{_safe_yaml_single_quoted(msg)}'\n")
        lines.append("  languages:\n")
        lines.append(lang_yaml + "\n")
        lines.append(f"  severity: {rule.semgrep_severity}\n")
        lines.append("  metadata:\n")
        lines.append("    category: inclusive-language\n")
        lines.append(f"    subcategory: {rule.category}\n")
        lines.append(f"    alternative: {rule.primary_alt}\n")
        if rule.severity in ("error", "warning"):
            lines.append("  fix-regex:\n")
            lines.append(f"    regex: {rule.regex}\n")
            lines.append(f"    replacement: {rule.primary_alt}\n")
    output_path.write_text("".join(lines))


def generate_python(rules: list[Rule], output_path: Path) -> None:
    _generate_lang_file(rules, output_path, "Python", "animal-violence.python.string", ["python"])


def generate_javascript(rules: list[Rule], output_path: Path) -> None:
    _generate_lang_file(
        rules, output_path, "JavaScript/TypeScript",
        "animal-violence.javascript.string", ["javascript", "typescript"],
    )


def generate_go(rules: list[Rule], output_path: Path) -> None:
    _generate_lang_file(rules, output_path, "Go", "animal-violence.go.string", ["go"])


def main() -> int:
    rules = load_rules(canonical_rules_path())
    generate_generic(rules, BUILD_DIR / "animal-violence-generic.yaml")
    generate_python(rules, BUILD_DIR / "animal-violence-python.yaml")
    generate_javascript(rules, BUILD_DIR / "animal-violence-javascript.yaml")
    generate_go(rules, BUILD_DIR / "animal-violence-go.yaml")
    print(f"Semgrep: wrote 4 files to {BUILD_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
