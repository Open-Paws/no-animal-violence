"""Golden-file tests for all generators."""
import sys
from pathlib import Path

import yaml

FIXTURES = Path(__file__).parent / "fixtures"
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
GENERATORS = REPO_ROOT / "tools" / "generators"

sys.path.insert(0, str(GENERATORS))
from loader import load_rules  # noqa: E402


def test_load_rules_mini():
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    assert len(rules) == 3
    names = {r.name for r in rules}
    assert names == {"guinea-pig", "livestock", "curiosity-killed-the-cat"}


def test_rule_fields():
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    gp = next(r for r in rules if r.name == "guinea-pig")
    assert gp.severity == "warning"
    assert gp.category == "animal-violence"
    assert gp.regex == r"guinea\s+pig"
    assert gp.word_boundary is True
    assert gp.primary_term == "guinea pig"
    assert gp.primary_alt == "test subject"
    assert gp.semgrep_severity == "WARNING"


def test_semgrep_generic_output(tmp_path):
    """gen_semgrep produces valid YAML with correct rule IDs and severities."""
    from gen_semgrep import generate_generic
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "animal-violence-generic.yaml"
    generate_generic(rules, output_path)
    with open(output_path) as f:
        data = yaml.safe_load(f)
    rule_ids = {r["id"] for r in data["rules"]}
    assert "animal-violence.guinea-pig" in rule_ids
    assert "animal-violence.livestock" in rule_ids
    gp_rule = next(r for r in data["rules"] if r["id"] == "animal-violence.guinea-pig")
    assert gp_rule["severity"] == "WARNING"
    cat_rule = next(r for r in data["rules"] if r["id"] == "animal-violence.curiosity-killed-the-cat")
    assert cat_rule["severity"] == "ERROR"


def test_pre_commit_output(tmp_path):
    """gen_pre_commit produces valid Python with correct patterns."""
    from gen_pre_commit import generate
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "no_animal_violence_check.py"
    generate(rules, output_path)
    content = output_path.read_text()
    assert "AUTO-GENERATED" in content
    assert r"guinea\s+pig" in content
    assert "test subject" in content
    assert "livestock" in content


def test_vale_output(tmp_path):
    """gen_vale produces valid YAML with all terms as swap keys."""
    from gen_vale import generate_downstream
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "AnimalIdioms.yml"
    generate_downstream(rules, output_path)
    with open(output_path) as f:
        data = yaml.safe_load(f)
    assert "swap" in data
    assert "guinea pig" in data["swap"]
    assert data["swap"]["guinea pig"] == "test subject"


def test_semgrep_python_has_fix_regex(tmp_path):
    """Python semgrep rules include fix-regex for error severity."""
    from gen_semgrep import generate_python
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "animal-violence-python.yaml"
    generate_python(rules, output_path)
    content = output_path.read_text()
    assert "fix-regex" in content
    assert "livestock" in content


def test_semgrep_generic_has_autofix_note(tmp_path):
    """Generic semgrep message includes autofix note for error/warning."""
    from gen_semgrep import generate_generic
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "animal-violence-generic.yaml"
    generate_generic(rules, output_path)
    content = output_path.read_text()
    assert "(autofix available)" in content


def test_vale_all_terms_present(tmp_path):
    """Vale swap map includes all terms from all rules."""
    from gen_vale import generate_downstream
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "AnimalIdioms.yml"
    generate_downstream(rules, output_path)
    with open(output_path) as f:
        data = yaml.safe_load(f)
    assert "guinea pig" in data["swap"]
    assert "livestock" in data["swap"]
    assert "curiosity killed the cat" in data["swap"]
