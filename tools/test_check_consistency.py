#!/usr/bin/env python3
"""Tests for the cross-format consistency checker."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest import TestCase, main

import yaml

from check_consistency import (
    CanonicalRule,
    DriftFinding,
    DriftReport,
    check_eslint,
    check_semgrep,
    check_vale,
    load_canonical,
    normalize_term,
    run_check,
)


def make_canonical(rules_data: list[dict]) -> Path:
    """Create a temporary canonical repo with woke rules."""
    tmpdir = Path(tempfile.mkdtemp())
    woke_dir = tmpdir / "woke"
    woke_dir.mkdir()
    woke_file = woke_dir / ".woke.yaml"
    with open(woke_file, "w") as f:
        yaml.dump({"rules": rules_data}, f)
    return tmpdir


def make_eslint(terms: dict[str, str]) -> Path:
    """Create a temporary ESLint plugin with given terms."""
    tmpdir = Path(tempfile.mkdtemp())
    eslint_dir = tmpdir / "eslint-plugin-no-animal-violence" / "lib" / "rules"
    eslint_dir.mkdir(parents=True)
    entries = ", ".join(f'["{t}", "{a}"]' for t, a in terms.items())
    content = f"""
const VIOLENT_ANIMAL_PHRASES = new Map([{entries}]);
module.exports = {{}};
"""
    (eslint_dir / "no-violent-language.js").write_text(content)
    return tmpdir


def make_semgrep(rules: list[dict]) -> Path:
    """Create a temporary Semgrep rules directory."""
    tmpdir = Path(tempfile.mkdtemp())
    rules_dir = tmpdir / "semgrep-rules-no-animal-violence" / "rules"
    rules_dir.mkdir(parents=True)
    with open(rules_dir / "animal-violence-generic.yaml", "w") as f:
        yaml.dump({"rules": rules}, f)
    return tmpdir


def make_vale(swaps: dict[str, str], filename: str = "AnimalIdioms.yml") -> Path:
    """Create a temporary Vale rules directory."""
    tmpdir = Path(tempfile.mkdtemp())
    vale_dir = tmpdir / "vale-no-animal-violence" / "Speciesism"
    vale_dir.mkdir(parents=True)
    data = {
        "extends": "substitution",
        "message": "test",
        "level": "warning",
        "ignorecase": True,
        "swap": swaps,
    }
    with open(vale_dir / filename, "w") as f:
        yaml.dump(data, f)
    # Also need meta.json
    with open(vale_dir / "meta.json", "w") as f:
        json.dump({"vale_version": ">=2.0.0"}, f)
    return tmpdir


class TempDirTestCase(TestCase):
    """Base test case that tracks and cleans up temporary directories."""

    def setUp(self):
        super().setUp()
        self._temp_dirs: list[Path] = []

    def tearDown(self):
        for tmpdir in self._temp_dirs:
            shutil.rmtree(tmpdir, ignore_errors=True)
        super().tearDown()

    def track(self, path: Path) -> Path:
        """Register a temp directory for cleanup and return it."""
        self._temp_dirs.append(path)
        return path


SAMPLE_CANONICAL = [
    {
        "name": "kill-two-birds",
        "terms": ["kill two birds with one stone"],
        "alternatives": ["accomplish two things at once"],
        "severity": "error",
        "options": {"word_boundary": False, "categories": ["animal-violence"]},
    },
    {
        "name": "guinea-pig",
        "terms": ["guinea pig"],
        "alternatives": ["test subject"],
        "severity": "warning",
        "options": {"word_boundary": True, "categories": ["animal-violence"]},
    },
    {
        "name": "livestock",
        "terms": ["livestock"],
        "alternatives": ["farmed animals"],
        "severity": "warning",
        "options": {"word_boundary": True, "categories": ["industry-euphemism"]},
    },
]


class TestNormalizeTerm(TempDirTestCase):
    def test_lowercase(self):
        self.assertEqual(normalize_term("Kill Two Birds"), "kill two birds")

    def test_collapse_whitespace(self):
        self.assertEqual(normalize_term("kill  two   birds"), "kill two birds")

    def test_strip(self):
        self.assertEqual(normalize_term("  livestock  "), "livestock")


class TestLoadCanonical(TempDirTestCase):
    def test_loads_rules(self):
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        rules = load_canonical(repo_dir)
        self.assertEqual(len(rules), 3)
        self.assertEqual(rules[0].name, "kill-two-birds")
        self.assertEqual(rules[0].primary_term, "kill two birds with one stone")
        self.assertEqual(rules[0].alternatives, ["accomplish two things at once"])
        self.assertEqual(rules[0].category, "animal-violence")

    def test_category_from_options(self):
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        rules = load_canonical(repo_dir)
        self.assertEqual(rules[2].category, "industry-euphemism")

    def test_missing_file(self):
        repo_dir = self.track(Path(tempfile.mkdtemp()))
        rules = load_canonical(repo_dir)
        self.assertEqual(rules, [])

    def test_malformed_yaml(self):
        repo_dir = self.track(Path(tempfile.mkdtemp()))
        woke_dir = repo_dir / "woke"
        woke_dir.mkdir()
        (woke_dir / ".woke.yaml").write_text(": invalid: yaml: [")
        rules = load_canonical(repo_dir)
        self.assertEqual(rules, [])


class TestCheckEslint(TempDirTestCase):
    def test_perfect_match(self):
        """ESLint has exactly the same rules — no drift."""
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        canonical = load_canonical(repo_dir)
        repos_dir = self.track(make_eslint({
            "kill two birds with one stone": "accomplish two things at once",
            "guinea pig": "test subject",
            "livestock": "farmed animals",
        }))
        findings = check_eslint(canonical, repos_dir)
        self.assertEqual(len(findings), 0)

    def test_missing_rule(self):
        """ESLint is missing 'livestock' — should report drift."""
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        canonical = load_canonical(repo_dir)
        repos_dir = self.track(make_eslint({
            "kill two birds with one stone": "accomplish two things at once",
            "guinea pig": "test subject",
        }))
        findings = check_eslint(canonical, repos_dir)
        missing = [f for f in findings if f.kind == "missing"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0].rule_name, "livestock")

    def test_extra_rule(self):
        """ESLint has a rule not in canonical — should report drift."""
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        canonical = load_canonical(repo_dir)
        repos_dir = self.track(make_eslint({
            "kill two birds with one stone": "accomplish two things at once",
            "guinea pig": "test subject",
            "livestock": "farmed animals",
            "some extra phrase": "replacement",
        }))
        findings = check_eslint(canonical, repos_dir)
        extra = [f for f in findings if f.kind == "extra"]
        self.assertEqual(len(extra), 1)
        self.assertIn("some extra phrase", extra[0].detail)

    def test_alternative_mismatch(self):
        """ESLint has different alternative — should report drift."""
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        canonical = load_canonical(repo_dir)
        repos_dir = self.track(make_eslint({
            "kill two birds with one stone": "wrong alternative",
            "guinea pig": "test subject",
            "livestock": "farmed animals",
        }))
        findings = check_eslint(canonical, repos_dir)
        mismatches = [f for f in findings if f.kind == "alternative_mismatch"]
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0].rule_name, "kill-two-birds")

    def test_missing_repo(self):
        """ESLint repo doesn't exist — should report gracefully."""
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        canonical = load_canonical(repo_dir)
        repos_dir = self.track(Path(tempfile.mkdtemp()))  # Empty dir
        findings = check_eslint(canonical, repos_dir)
        self.assertTrue(any(f.kind == "missing" and f.rule_name == "*" for f in findings))


class TestCheckSemgrep(TempDirTestCase):
    def test_perfect_match(self):
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        canonical = load_canonical(repo_dir)
        repos_dir = self.track(make_semgrep([
            {
                "id": "animal-violence.kill-two-birds",
                "pattern-regex": "kill\\s+two\\s+birds",
                "languages": ["generic"],
                "severity": "ERROR",
                "metadata": {"alternative": "accomplish two things at once"},
            },
            {
                "id": "animal-violence.guinea-pig",
                "pattern-regex": "guinea\\s+pig",
                "languages": ["generic"],
                "severity": "WARNING",
                "metadata": {"alternative": "test subject"},
            },
            {
                "id": "animal-violence.livestock",
                "pattern-regex": "\\blivestock\\b",
                "languages": ["generic"],
                "severity": "WARNING",
                "metadata": {"alternative": "farmed animals"},
            },
        ]))
        findings = check_semgrep(canonical, repos_dir)
        self.assertEqual(len(findings), 0)

    def test_missing_rule(self):
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        canonical = load_canonical(repo_dir)
        repos_dir = self.track(make_semgrep([
            {
                "id": "animal-violence.kill-two-birds",
                "pattern-regex": "kill\\s+two\\s+birds",
                "languages": ["generic"],
                "severity": "ERROR",
                "metadata": {"alternative": "accomplish two things at once"},
            },
        ]))
        findings = check_semgrep(canonical, repos_dir)
        missing = [f for f in findings if f.kind == "missing"]
        self.assertEqual(len(missing), 2)  # guinea-pig and livestock


class TestCheckVale(TempDirTestCase):
    def test_perfect_match(self):
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        canonical = load_canonical(repo_dir)
        repos_dir = self.track(make_vale({
            "kill two birds with one stone": "accomplish two things at once",
            "guinea pig": "test subject",
            "livestock": "farmed animals",
        }))
        findings = check_vale(canonical, repos_dir)
        self.assertEqual(len(findings), 0)

    def test_missing_rule(self):
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        canonical = load_canonical(repo_dir)
        repos_dir = self.track(make_vale({
            "kill two birds with one stone": "accomplish two things at once",
        }))
        findings = check_vale(canonical, repos_dir)
        missing = [f for f in findings if f.kind == "missing"]
        self.assertEqual(len(missing), 2)

    def test_alternative_mismatch(self):
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))
        canonical = load_canonical(repo_dir)
        repos_dir = self.track(make_vale({
            "kill two birds with one stone": "different alternative",
            "guinea pig": "test subject",
            "livestock": "farmed animals",
        }))
        findings = check_vale(canonical, repos_dir)
        mismatches = [f for f in findings if f.kind == "alternative_mismatch"]
        self.assertEqual(len(mismatches), 1)


class TestDriftReport(TempDirTestCase):
    def test_no_drift(self):
        report = DriftReport(canonical_count=3)
        self.assertFalse(report.has_drift)
        self.assertIn("No drift detected", report.summary())

    def test_with_drift(self):
        report = DriftReport(
            canonical_count=3,
            findings=[
                DriftFinding("eslint", "livestock", "missing", "Not found"),
            ],
        )
        self.assertTrue(report.has_drift)
        self.assertIn("Drift findings: 1", report.summary())
        self.assertIn("[eslint]", report.summary())


class TestRunCheckIntegration(TempDirTestCase):
    """Integration test using synthetic repos with known drift."""

    def test_detects_known_drift(self):
        """Create synthetic repos with intentional drift and verify detection."""
        repo_dir = self.track(make_canonical(SAMPLE_CANONICAL))

        # ESLint: missing livestock
        repos_dir = self.track(Path(tempfile.mkdtemp()))
        eslint_dir = repos_dir / "eslint-plugin-no-animal-violence" / "lib" / "rules"
        eslint_dir.mkdir(parents=True)
        (eslint_dir / "no-violent-language.js").write_text("""
const VIOLENT_ANIMAL_PHRASES = new Map([
    ["kill two birds with one stone", "accomplish two things at once"],
    ["guinea pig", "test subject"],
]);
module.exports = {};
""")

        # Semgrep: has all 3 but wrong alternative for guinea-pig
        semgrep_dir = repos_dir / "semgrep-rules-no-animal-violence" / "rules"
        semgrep_dir.mkdir(parents=True)
        with open(semgrep_dir / "animal-violence-generic.yaml", "w") as f:
            yaml.dump({"rules": [
                {"id": "animal-violence.kill-two-birds", "pattern-regex": "test",
                 "languages": ["generic"], "severity": "ERROR",
                 "metadata": {"alternative": "accomplish two things at once"}},
                {"id": "animal-violence.guinea-pig", "pattern-regex": "test",
                 "languages": ["generic"], "severity": "WARNING",
                 "metadata": {"alternative": "early adopter"}},  # WRONG
                {"id": "animal-violence.livestock", "pattern-regex": "test",
                 "languages": ["generic"], "severity": "WARNING",
                 "metadata": {"alternative": "farmed animals"}},
            ]}, f)

        # Vale: missing guinea-pig entirely
        vale_dir = repos_dir / "vale-no-animal-violence" / "Speciesism"
        vale_dir.mkdir(parents=True)
        with open(vale_dir / "Rules.yml", "w") as f:
            yaml.dump({
                "extends": "substitution",
                "message": "test",
                "level": "warning",
                "ignorecase": True,
                "swap": {
                    "kill two birds with one stone": "accomplish two things at once",
                    "livestock": "farmed animals",
                },
            }, f)

        report = run_check(repo_dir, repos_dir)

        self.assertEqual(report.canonical_count, 3)
        self.assertTrue(report.has_drift)

        # ESLint should have 1 missing (livestock)
        eslint_missing = [f for f in report.findings
                          if f.downstream == "eslint" and f.kind == "missing"]
        self.assertEqual(len(eslint_missing), 1)
        self.assertEqual(eslint_missing[0].rule_name, "livestock")

        # Semgrep should have 1 mismatch (guinea-pig)
        semgrep_mismatches = [f for f in report.findings
                              if f.downstream == "semgrep" and f.kind == "alternative_mismatch"]
        self.assertEqual(len(semgrep_mismatches), 1)
        self.assertEqual(semgrep_mismatches[0].rule_name, "guinea-pig")

        # Vale should have 1 missing (guinea-pig)
        vale_missing = [f for f in report.findings
                        if "vale" in f.downstream and f.kind == "missing"]
        self.assertEqual(len(vale_missing), 1)
        self.assertEqual(vale_missing[0].rule_name, "guinea-pig")


if __name__ == "__main__":
    main()
