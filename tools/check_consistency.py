#!/usr/bin/env python3
"""Cross-format consistency checker for the no-animal-violence suite.

Reads the canonical rule set from rules.yaml and checks downstream
repos (ESLint, Semgrep, Vale) for drift: missing rules, extra rules,
and alternative mismatches.

Usage:
    python tools/check_consistency.py [--repos-dir /path/to/repos] [--skip-clone] [--json]

By default, looks for sibling directories:
    ../eslint-plugin-no-animal-violence
    ../semgrep-rules-no-animal-violence
    ../vale-no-animal-violence

With --skip-clone (or when repos are already present locally), performs a direct
file comparison without cloning. Without --skip-clone and with network access,
can be extended to shallow-clone repos for comparison.
"""

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import yaml

# Make generators importable when run from repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "tools" / "generators"))

try:
    from loader import Rule, load_rules
    _LOADER_AVAILABLE = True
except ImportError:
    _LOADER_AVAILABLE = False

logger = logging.getLogger(__name__)


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

        by_downstream: dict[str, list[DriftFinding]] = {}
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


def _load_canonical(repo_dir: Path) -> list[Rule]:
    """Load canonical rules from rules.yaml (preferred) or woke/.woke.yaml (fallback)."""
    rules_yaml = repo_dir / "rules.yaml"
    if _LOADER_AVAILABLE and rules_yaml.exists():
        return load_rules(rules_yaml)

    # Fallback: load from woke/.woke.yaml
    woke_path = repo_dir / "woke" / ".woke.yaml"
    try:
        with open(woke_path) as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("Neither rules.yaml nor woke/.woke.yaml found in %s", repo_dir)
        return []
    except yaml.YAMLError as exc:
        logger.error("Failed to parse woke rules: %s", exc)
        return []

    rules = []
    for entry in data.get("rules", []):
        category = "animal-violence"
        cats = entry.get("options", {}).get("categories", [])
        if cats:
            category = cats[0]
        terms = [t.lower() for t in entry.get("terms", [])]
        alternatives = [a.lower() for a in entry.get("alternatives", [])]
        r = SimpleNamespace(
            name=entry["name"],
            terms=terms,
            alternatives=alternatives,
            severity=entry.get("severity", "info"),
            category=category,
            primary_term=terms[0] if terms else "",
            primary_alt=alternatives[0] if alternatives else "",
        )
        rules.append(r)
    return rules


def normalize_term(term: str) -> str:
    """Normalize a term for comparison: lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", term.lower().strip())


def _extract_eslint_terms(content: str) -> dict[str, str]:
    """Extract {normalized_term: alternative} from ESLint plugin JS source."""
    terms = {}
    for match in re.finditer(r'\["([^"]+)",\s*"([^"]+)"\]', content):
        term = normalize_term(match.group(1))
        alt = match.group(2).lower().strip()
        terms[term] = alt
    return terms


def _collect_canonical_terms(canonical: list) -> set[str]:
    """Return the set of all normalized terms from canonical rules."""
    return {normalize_term(t) for rule in canonical for t in rule.terms}


def _check_eslint_coverage(rule, eslint_terms: dict[str, str]) -> DriftFinding | None:
    primary = normalize_term(rule.primary_term)
    if primary in eslint_terms:
        eslint_alt = eslint_terms[primary]
        canonical_primary_alt = rule.alternatives[0].lower() if rule.alternatives else ""
        if eslint_alt != canonical_primary_alt:
            return DriftFinding(
                downstream="eslint",
                rule_name=rule.name,
                kind="alternative_mismatch",
                detail=f"canonical='{canonical_primary_alt}', eslint='{eslint_alt}'",
            )
        return None
    if any(normalize_term(t) in eslint_terms for t in rule.terms):
        return None
    return DriftFinding(
        downstream="eslint",
        rule_name=rule.name,
        kind="missing",
        detail=f"Term '{primary}' not found in ESLint plugin",
    )


def check_eslint(canonical: list, repos_dir: Path) -> list[DriftFinding]:
    """Check ESLint plugin for drift against canonical rules."""
    rule_file = repos_dir / "eslint-plugin-no-animal-violence" / "lib" / "rules" / "no-violent-language.js"
    findings = []

    if not rule_file.exists():
        return [DriftFinding(
            downstream="eslint",
            rule_name="*",
            kind="missing",
            detail=f"Rule file not found: {rule_file}",
        )]

    eslint_terms = _extract_eslint_terms(rule_file.read_text())
    findings.extend(filter(None, (_check_eslint_coverage(r, eslint_terms) for r in canonical)))

    canonical_terms = _collect_canonical_terms(canonical)
    findings.extend(
        DriftFinding(
            downstream="eslint",
            rule_name=term,
            kind="extra",
            detail=f"Term '{term}' in ESLint but not in canonical",
        )
        for term in eslint_terms
        if term not in canonical_terms
    )
    return findings


_SEMGREP_ID_PREFIX = "animal-violence."


def _parse_semgrep_rules(generic_file: Path) -> tuple[dict, DriftFinding | None]:
    try:
        with open(generic_file) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        return {}, DriftFinding(
            downstream="semgrep",
            rule_name="*",
            kind="missing",
            detail=f"Failed to parse Semgrep rules: {exc}",
        )
    rules = {}
    for entry in data.get("rules", []):
        rule_id = entry.get("id", "")
        short_name = rule_id.removeprefix(_SEMGREP_ID_PREFIX)
        rules[short_name] = {
            "id": rule_id,
            "pattern": entry.get("pattern-regex", ""),
            "alternative": entry.get("metadata", {}).get("alternative", "").lower(),
        }
    return rules, None


def _check_semgrep_rule(rule, semgrep_rules: dict) -> DriftFinding | None:
    if rule.name not in semgrep_rules:
        return DriftFinding(
            downstream="semgrep",
            rule_name=rule.name,
            kind="missing",
            detail=f"Rule '{rule.name}' not found in Semgrep generic rules",
        )
    semgrep_alt = semgrep_rules[rule.name]["alternative"]
    canonical_primary_alt = rule.alternatives[0].lower() if rule.alternatives else ""
    if semgrep_alt and canonical_primary_alt and semgrep_alt != canonical_primary_alt:
        return DriftFinding(
            downstream="semgrep",
            rule_name=rule.name,
            kind="alternative_mismatch",
            detail=f"canonical='{canonical_primary_alt}', semgrep='{semgrep_alt}'",
        )
    return None


def check_semgrep(canonical: list, repos_dir: Path) -> list[DriftFinding]:
    """Check Semgrep rules for drift against canonical rules."""
    semgrep_dir = repos_dir / "semgrep-rules-no-animal-violence" / "rules"
    generic_file = semgrep_dir / "animal-violence-generic.yaml"

    if not semgrep_dir.exists():
        return [DriftFinding(downstream="semgrep", rule_name="*", kind="missing",
                             detail=f"Rules directory not found: {semgrep_dir}")]
    if not generic_file.exists():
        return [DriftFinding(downstream="semgrep", rule_name="*", kind="missing",
                             detail=f"Generic rules file not found: {generic_file}")]

    semgrep_rules, parse_error = _parse_semgrep_rules(generic_file)
    if parse_error is not None:
        return [parse_error]

    findings = list(filter(None, (_check_semgrep_rule(r, semgrep_rules) for r in canonical)))
    canonical_names = {r.name for r in canonical}
    findings.extend(
        DriftFinding(
            downstream="semgrep",
            rule_name=name,
            kind="extra",
            detail=f"Rule '{name}' in Semgrep but not in canonical",
        )
        for name in semgrep_rules
        if name not in canonical_names
    )
    return findings


def _clean_vale_term(term: str) -> str:
    clean = re.sub(r"[\\()]", "", term).lower().strip()
    clean = re.sub(r"\\?:", "", clean)
    return re.sub(r"[?+*]", "", clean)


def _load_vale_terms(vale_dir: Path) -> tuple[dict[str, str], list[str]]:
    terms: dict[str, str] = {}
    parse_errors: list[str] = []
    for yml_file in vale_dir.rglob("*.yml"):
        try:
            with open(yml_file) as f:
                data = yaml.safe_load(f)
            if data and "swap" in data:
                for term, alt in data["swap"].items():
                    terms[_clean_vale_term(term)] = alt.lower() if isinstance(alt, str) else str(alt).lower()
        except (yaml.YAMLError, OSError) as exc:
            parse_errors.append(f"{yml_file}: {exc}")
    return terms, parse_errors


def _check_vale_coverage(rule, vale_terms: dict[str, str], label: str) -> DriftFinding | None:
    for term in rule.terms:
        nt = normalize_term(term)
        if nt in vale_terms:
            canonical_primary_alt = rule.alternatives[0].lower() if rule.alternatives else ""
            vale_alt = vale_terms[nt]
            if canonical_primary_alt and vale_alt != canonical_primary_alt:
                return DriftFinding(
                    downstream=label,
                    rule_name=rule.name,
                    kind="alternative_mismatch",
                    detail=f"canonical='{canonical_primary_alt}', vale='{vale_alt}'",
                )
            return None
    primary = normalize_term(rule.primary_term)
    return DriftFinding(
        downstream=label,
        rule_name=rule.name,
        kind="missing",
        detail=f"Term '{primary}' not found in Vale rules",
    )


def check_vale(canonical: list, repos_dir: Path) -> list[DriftFinding]:
    findings = []
    for vale_dir in [repos_dir / "vale-no-animal-violence"]:
        label = f"vale ({vale_dir.name})"
        if not vale_dir.exists():
            findings.append(DriftFinding(
                downstream=label, rule_name="*", kind="missing",
                detail=f"Vale directory not found: {vale_dir}",
            ))
            continue
        vale_terms, parse_errors = _load_vale_terms(vale_dir)
        for err in parse_errors:
            logger.warning("Vale parse error: %s", err)
        findings.extend(filter(None, (_check_vale_coverage(r, vale_terms, label) for r in canonical)))
    return findings


def run_check(repo_dir: Path, repos_dir: Path) -> DriftReport:
    """Run full consistency check and return a report."""
    canonical = _load_canonical(repo_dir)
    report = DriftReport(canonical_count=len(canonical))

    # ESLint
    report.findings.extend(check_eslint(canonical, repos_dir))
    eslint_file = repos_dir / "eslint-plugin-no-animal-violence" / "lib" / "rules" / "no-violent-language.js"
    if eslint_file.exists():
        content = eslint_file.read_text()
        report.downstream_counts["eslint"] = len(re.findall(r'\["[^"]+",\s*"[^"]+"', content))

    # Semgrep
    report.findings.extend(check_semgrep(canonical, repos_dir))
    semgrep_file = repos_dir / "semgrep-rules-no-animal-violence" / "rules" / "animal-violence-generic.yaml"
    if semgrep_file.exists():
        try:
            with open(semgrep_file) as f:
                data = yaml.safe_load(f)
            report.downstream_counts["semgrep (generic)"] = len(data.get("rules", []))
        except yaml.YAMLError:
            pass

    # Vale
    report.findings.extend(check_vale(canonical, repos_dir))
    vale_dir = repos_dir / "vale-no-animal-violence"
    if vale_dir.exists():
        count = 0
        for yml_file in vale_dir.rglob("*.yml"):
            try:
                with open(yml_file) as f:
                    data = yaml.safe_load(f)
                if data and "swap" in data:
                    count += len(data["swap"])
            except (yaml.YAMLError, OSError):
                continue
        report.downstream_counts["vale"] = count

    return report


def main() -> int:
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
        "--skip-clone",
        action="store_true",
        help="Skip cloning; compare against already-present local repos only",
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

    return 1 if report.has_drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
