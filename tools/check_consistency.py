#!/usr/bin/env python3
"""
Cross-format consistency checker for the no-animal-violence suite.

Reads the canonical rule set from woke/.woke.yaml and checks downstream
repos (ESLint, Semgrep, Vale) for drift: missing rules, extra rules,
and alternative mismatches.

Usage:
    python tools/check_consistency.py [--repos-dir /path/to/repos]

By default, looks for sibling directories:
    ../eslint-plugin-no-animal-violence
    ../semgrep-rules-no-animal-violence
    ../vale-no-animal-violence
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class CanonicalRule:
    """A rule from the canonical woke/.woke.yaml dictionary."""
    name: str
    terms: list[str]
    alternatives: list[str]
    severity: str
    category: str

    @property
    def primary_term(self) -> str:
        return self.terms[0] if self.terms else ""


@dataclass
class DriftFinding:
    """A single consistency issue found in a downstream repo."""
    downstream: str
    rule_name: str
    kind: str  # "missing", "extra", "alternative_mismatch"
    detail: str


@dataclass
class DriftReport:
    """Aggregated drift findings across all downstream repos."""
    canonical_count: int = 0
    findings: list[DriftFinding] = field(default_factory=list)
    downstream_counts: dict[str, int] = field(default_factory=dict)

    @property
    def has_drift(self) -> bool:
        return len(self.findings) > 0

    def summary(self) -> str:
        lines = [
            f"Canonical rules: {self.canonical_count}",
            "",
        ]
        for ds, count in sorted(self.downstream_counts.items()):
            lines.append(f"{ds}: {count} rules")

        if not self.findings:
            lines.append("\nNo drift detected. All formats are consistent.")
            return "\n".join(lines)

        lines.append(f"\nDrift findings: {len(self.findings)}")
        lines.append("-" * 60)

        by_downstream = {}
        for f in self.findings:
            by_downstream.setdefault(f.downstream, []).append(f)

        for ds in sorted(by_downstream):
            findings = by_downstream[ds]
            missing = [f for f in findings if f.kind == "missing"]
            extra = [f for f in findings if f.kind == "extra"]
            mismatches = [f for f in findings if f.kind == "alternative_mismatch"]

            lines.append(f"\n[{ds}]")
            if missing:
                lines.append(f"  Missing ({len(missing)}):")
                for f in missing:
                    lines.append(f"    - {f.rule_name}: {f.detail}")
            if extra:
                lines.append(f"  Extra ({len(extra)}):")
                for f in extra:
                    lines.append(f"    - {f.rule_name}: {f.detail}")
            if mismatches:
                lines.append(f"  Alternative mismatches ({len(mismatches)}):")
                for f in mismatches:
                    lines.append(f"    - {f.rule_name}: {f.detail}")

        return "\n".join(lines)


def load_canonical(repo_dir: Path) -> list[CanonicalRule]:
    """Load canonical rules from woke/.woke.yaml."""
    woke_path = repo_dir / "woke" / ".woke.yaml"
    with open(woke_path) as f:
        data = yaml.safe_load(f)

    rules = []
    for entry in data.get("rules", []):
        category = "animal-violence"
        cats = entry.get("options", {}).get("categories", [])
        if cats:
            category = cats[0]
        rules.append(CanonicalRule(
            name=entry["name"],
            terms=[t.lower() for t in entry.get("terms", [])],
            alternatives=[a.lower() for a in entry.get("alternatives", [])],
            severity=entry.get("severity", "info"),
            category=category,
        ))
    return rules


def normalize_term(term: str) -> str:
    """Normalize a term for comparison: lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", term.lower().strip())


def check_eslint(canonical: list[CanonicalRule], repos_dir: Path) -> list[DriftFinding]:
    """Check ESLint plugin for drift against canonical rules."""
    eslint_dir = repos_dir / "eslint-plugin-no-animal-violence"
    rule_file = eslint_dir / "lib" / "rules" / "no-violent-language.js"
    findings = []

    if not rule_file.exists():
        findings.append(DriftFinding(
            downstream="eslint",
            rule_name="*",
            kind="missing",
            detail=f"Rule file not found: {rule_file}",
        ))
        return findings

    content = rule_file.read_text()

    # Extract Map entries: ["phrase", "alternative"]
    eslint_terms = {}
    for match in re.finditer(r'\["([^"]+)",\s*"([^"]+)"\]', content):
        term = normalize_term(match.group(1))
        alt = match.group(2).lower().strip()
        eslint_terms[term] = alt

    # Check each canonical rule
    for rule in canonical:
        primary = normalize_term(rule.primary_term)
        if primary in eslint_terms:
            # Check if the primary alternative matches
            eslint_alt = eslint_terms[primary]
            canonical_primary_alt = rule.alternatives[0].lower() if rule.alternatives else ""
            if eslint_alt != canonical_primary_alt:
                findings.append(DriftFinding(
                    downstream="eslint",
                    rule_name=rule.name,
                    kind="alternative_mismatch",
                    detail=f"canonical='{canonical_primary_alt}', eslint='{eslint_alt}'",
                ))
        else:
            # Check if any term variant matches
            found = False
            for term in rule.terms:
                if normalize_term(term) in eslint_terms:
                    found = True
                    break
            if not found:
                findings.append(DriftFinding(
                    downstream="eslint",
                    rule_name=rule.name,
                    kind="missing",
                    detail=f"Term '{primary}' not found in ESLint plugin",
                ))

    # Check for extra rules in ESLint not in canonical
    canonical_terms = set()
    for rule in canonical:
        for term in rule.terms:
            canonical_terms.add(normalize_term(term))

    for eslint_term in eslint_terms:
        if eslint_term not in canonical_terms:
            findings.append(DriftFinding(
                downstream="eslint",
                rule_name=eslint_term,
                kind="extra",
                detail=f"Term '{eslint_term}' in ESLint but not in canonical",
            ))

    return findings


def check_semgrep(canonical: list[CanonicalRule], repos_dir: Path) -> list[DriftFinding]:
    """Check Semgrep rules for drift against canonical rules."""
    semgrep_dir = repos_dir / "semgrep-rules-no-animal-violence" / "rules"
    findings = []

    if not semgrep_dir.exists():
        findings.append(DriftFinding(
            downstream="semgrep",
            rule_name="*",
            kind="missing",
            detail=f"Rules directory not found: {semgrep_dir}",
        ))
        return findings

    # Load the generic rules file (most comparable to canonical)
    generic_file = semgrep_dir / "animal-violence-generic.yaml"
    if not generic_file.exists():
        findings.append(DriftFinding(
            downstream="semgrep",
            rule_name="*",
            kind="missing",
            detail=f"Generic rules file not found: {generic_file}",
        ))
        return findings

    with open(generic_file) as f:
        data = yaml.safe_load(f)

    # Extract Semgrep rule IDs and their regex patterns
    semgrep_rules = {}
    for entry in data.get("rules", []):
        rule_id = entry.get("id", "")
        # Extract the short name from the ID (e.g., "animal-violence.kill-two-birds" -> "kill-two-birds")
        short_name = rule_id.replace("animal-violence.", "")
        pattern = entry.get("pattern-regex", "")
        alt = entry.get("metadata", {}).get("alternative", "")
        semgrep_rules[short_name] = {
            "id": rule_id,
            "pattern": pattern,
            "alternative": alt.lower(),
        }

    # Check each canonical rule against Semgrep
    for rule in canonical:
        if rule.name in semgrep_rules:
            semgrep_alt = semgrep_rules[rule.name]["alternative"]
            canonical_primary_alt = rule.alternatives[0].lower() if rule.alternatives else ""
            if semgrep_alt and canonical_primary_alt and semgrep_alt != canonical_primary_alt:
                findings.append(DriftFinding(
                    downstream="semgrep",
                    rule_name=rule.name,
                    kind="alternative_mismatch",
                    detail=f"canonical='{canonical_primary_alt}', semgrep='{semgrep_alt}'",
                ))
        else:
            findings.append(DriftFinding(
                downstream="semgrep",
                rule_name=rule.name,
                kind="missing",
                detail=f"Rule '{rule.name}' not found in Semgrep generic rules",
            ))

    # Check for extra Semgrep rules
    canonical_names = {r.name for r in canonical}
    for semgrep_name in semgrep_rules:
        if semgrep_name not in canonical_names:
            findings.append(DriftFinding(
                downstream="semgrep",
                rule_name=semgrep_name,
                kind="extra",
                detail=f"Rule '{semgrep_name}' in Semgrep but not in canonical",
            ))

    return findings


def check_vale(canonical: list[CanonicalRule], repos_dir: Path) -> list[DriftFinding]:
    """Check Vale rules for drift against canonical rules."""
    findings = []

    # Check both the downstream vale repo AND the in-repo vale directory
    vale_dirs = [
        repos_dir / "vale-no-animal-violence",
    ]

    for vale_dir in vale_dirs:
        if not vale_dir.exists():
            findings.append(DriftFinding(
                downstream=f"vale ({vale_dir.name})",
                rule_name="*",
                kind="missing",
                detail=f"Vale directory not found: {vale_dir}",
            ))
            continue

        # Find all Vale YAML files (skip meta.json, README)
        vale_terms = {}
        label = f"vale ({vale_dir.name})"

        for yml_file in vale_dir.rglob("*.yml"):
            if yml_file.name == "meta.json":
                continue
            try:
                with open(yml_file) as f:
                    data = yaml.safe_load(f)
                if data and "swap" in data:
                    for term, alt in data["swap"].items():
                        # Strip YAML regex artifacts
                        clean_term = re.sub(r"[\\()]", "", term).lower().strip()
                        # Remove regex quantifiers like (?:ed|ing)?
                        clean_term = re.sub(r"\?\:", "", clean_term)
                        clean_term = re.sub(r"[?+*]", "", clean_term)
                        vale_terms[clean_term] = alt.lower() if isinstance(alt, str) else str(alt).lower()
            except Exception:
                pass

        # Check each canonical rule
        for rule in canonical:
            primary = normalize_term(rule.primary_term)
            found = False
            for term in rule.terms:
                nt = normalize_term(term)
                if nt in vale_terms:
                    found = True
                    vale_alt = vale_terms[nt]
                    canonical_primary_alt = rule.alternatives[0].lower() if rule.alternatives else ""
                    if canonical_primary_alt and vale_alt != canonical_primary_alt:
                        findings.append(DriftFinding(
                            downstream=label,
                            rule_name=rule.name,
                            kind="alternative_mismatch",
                            detail=f"canonical='{canonical_primary_alt}', vale='{vale_alt}'",
                        ))
                    break
            if not found:
                findings.append(DriftFinding(
                    downstream=label,
                    rule_name=rule.name,
                    kind="missing",
                    detail=f"Term '{primary}' not found in Vale rules",
                ))

    return findings


def run_check(repo_dir: Path, repos_dir: Path) -> DriftReport:
    """Run full consistency check and return a report."""
    canonical = load_canonical(repo_dir)
    report = DriftReport(canonical_count=len(canonical))

    # ESLint
    eslint_findings = check_eslint(canonical, repos_dir)
    report.findings.extend(eslint_findings)
    eslint_dir = repos_dir / "eslint-plugin-no-animal-violence" / "lib" / "rules" / "no-violent-language.js"
    if eslint_dir.exists():
        content = eslint_dir.read_text()
        report.downstream_counts["eslint"] = len(re.findall(r'\["[^"]+",\s*"[^"]+"', content))

    # Semgrep
    semgrep_findings = check_semgrep(canonical, repos_dir)
    report.findings.extend(semgrep_findings)
    semgrep_file = repos_dir / "semgrep-rules-no-animal-violence" / "rules" / "animal-violence-generic.yaml"
    if semgrep_file.exists():
        with open(semgrep_file) as f:
            data = yaml.safe_load(f)
        report.downstream_counts["semgrep (generic)"] = len(data.get("rules", []))

    # Vale
    vale_findings = check_vale(canonical, repos_dir)
    report.findings.extend(vale_findings)
    vale_dir = repos_dir / "vale-no-animal-violence"
    if vale_dir.exists():
        count = 0
        for yml_file in vale_dir.rglob("*.yml"):
            try:
                with open(yml_file) as f:
                    data = yaml.safe_load(f)
                if data and "swap" in data:
                    count += len(data["swap"])
            except Exception:
                pass
        report.downstream_counts["vale"] = count

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Check no-animal-violence suite consistency across formats"
    )
    parser.add_argument(
        "--repos-dir",
        type=Path,
        default=None,
        help="Directory containing sibling repos (default: parent of this repo)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parent.parent
    repos_dir = args.repos_dir or repo_dir.parent

    report = run_check(repo_dir, repos_dir)

    if args.json:
        output = {
            "canonical_count": report.canonical_count,
            "downstream_counts": report.downstream_counts,
            "drift_count": len(report.findings),
            "findings": [
                {
                    "downstream": f.downstream,
                    "rule": f.rule_name,
                    "kind": f.kind,
                    "detail": f.detail,
                }
                for f in report.findings
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(report.summary())

    sys.exit(1 if report.has_drift else 0)


if __name__ == "__main__":
    main()
