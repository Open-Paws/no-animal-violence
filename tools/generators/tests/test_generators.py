"""Golden-file tests for all generators."""
import re
import subprocess
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


def test_vscode_word_boundary_emission():
    """gen_vscode emits /\\b.../gi for word_boundary:true rules, not /\\\\b.../gi.

    Regression test for the double-escape bug: \\\\b in a JS template literal
    produces \\b in the string, which in a regex literal means literal backslash+b
    not a word boundary. The fix uses \\b → \\b in the output.
    """
    result = subprocess.run(
        ["node", str(GENERATORS / "gen_vscode.js")],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    output = (REPO_ROOT / "build" / "vscode-no-animal-violence" / "extension.js").read_text()
    # Double-escaped \\b must not appear — that was the broken form
    assert "/\\\\b" not in output, "Double-escaped \\\\b found — word boundary fix regressed"
    # At least one word_boundary:true rule must emit correct /\b...\b/gi form
    assert re.search(r"/\\b[^/]+\\b/gi", output), "No /\\b...\\b/gi pattern found — word boundaries missing"


def test_reviewdog_output_reformatter():
    """reformat_nav_output converts multi-line scanner output to file:line: message.

    Regression test for the reviewdog -efm format mismatch: the pre-commit checker
    outputs multi-line blocks but reviewdog -efm="%f:%l: %m" expects single-line
    entries. The reformatter must extract file, line, and found phrase.
    """
    from gen_reviewdog import reformat_nav_output
    sample = [
        "Animal violence language detected:\n",
        "\n",
        "  path/to/file.py:5\n",
        '    Found:   "guinea pig"\n',
        '    Suggest: "test subject"\n',
        "\n",
        "  another/file.md:12\n",
        '    Found:   "livestock"\n',
        '    Suggest: "farmed animals"\n',
        "\n",
        "2 instance(s) found.\n",
    ]
    result = reformat_nav_output(sample)
    assert result == [
        "path/to/file.py:5: guinea pig",
        "another/file.md:12: livestock",
    ]


def test_pre_commit_word_boundary(tmp_path):
    """gen_pre_commit wraps word_boundary:true patterns with \\b and leaves false ones bare."""
    from gen_pre_commit import generate
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "no_animal_violence_check.py"
    generate(rules, output_path)
    content = output_path.read_text()
    # guinea-pig has word_boundary:true — must have \b boundaries
    assert r'"regex": r"\b(?:guinea\s+pig)\b"' in content
    # curiosity-killed-the-cat has word_boundary:false — must NOT have \b
    assert r'"regex": r"curiosity\s+killed\s+the\s+cat"' in content
    assert r'\b(?:curiosity' not in content


def test_pre_commit_emits_reason(tmp_path):
    """gen_pre_commit emits the user-facing reason field for each pattern."""
    from gen_pre_commit import generate
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "no_animal_violence_check.py"
    generate(rules, output_path)
    content = output_path.read_text()
    assert '"reason":' in content
    assert "expendable test subjects" in content  # from guinea-pig reason in fixture
    assert "Why:" in content  # user-facing output includes reason


def test_semgrep_generic_includes_reason(tmp_path):
    """gen_semgrep embeds the reason in both message and metadata."""
    from gen_semgrep import generate_generic
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "animal-violence-generic.yaml"
    generate_generic(rules, output_path)
    content = output_path.read_text()
    assert "reason:" in content  # emitted as metadata key
    assert "expendable test subjects" in content  # appears in message and/or metadata


def test_vale_embeds_reason_as_comment(tmp_path):
    """gen_vale writes the reason as a YAML comment above each swap entry."""
    from gen_vale import generate_downstream
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "AnimalIdioms.yml"
    generate_downstream(rules, output_path)
    content = output_path.read_text()
    # Each rule should have a comment with its name and reason
    assert "# guinea-pig:" in content
    assert "expendable test subjects" in content


def test_loader_rejects_missing_reason(tmp_path):
    """loader.load_rules must fail loudly when a rule is missing its reason."""
    import pytest
    from loader import load_rules
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "version: '1.0.0'\n"
        "rules:\n"
        "  - name: no-reason\n"
        "    terms: ['foo']\n"
        "    alternatives: ['bar']\n"
        "    severity: info\n"
        "    category: animal-violence\n"
        "    word_boundary: true\n"
        "    regex: 'foo'\n"
    )
    with pytest.raises(ValueError, match="missing a non-empty 'reason'"):
        load_rules(bad)


def test_semgrep_generic_word_boundary(tmp_path):
    """gen_semgrep wraps word_boundary:true pattern-regex with \\b and leaves false ones bare."""
    from gen_semgrep import generate_generic
    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "animal-violence-generic.yaml"
    generate_generic(rules, output_path)
    content = output_path.read_text()
    # guinea-pig: word_boundary:true
    assert r"pattern-regex: '\b(?:guinea\s+pig)\b'" in content
    # curiosity: word_boundary:false — raw regex, no \b
    assert "pattern-regex: 'curiosity\\s+killed\\s+the\\s+cat'" in content
    assert r"\b(?:curiosity" not in content


def test_eslint_word_boundary(tmp_path):
    """gen_eslint emits per-rule patterns respecting word_boundary, using r.regex not r.terms[0]."""
    result = subprocess.run(
        ["node", str(GENERATORS / "gen_eslint.js")],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    output = (
        REPO_ROOT / "build" / "eslint-plugin-no-animal-violence"
        / "lib" / "rules" / "no-violent-language.js"
    ).read_text()
    # word_boundary:true — must use \b and the canonical regex (not the literal term)
    assert re.search(r"/\\bguinea\\s\+pig\\b/gi", output), "guinea-pig missing word boundaries or wrong pattern"
    # word_boundary:false — no \b
    assert re.search(r"/curiosity\\s\+killed\\s\+the\\s\+cat/gi", output)
    assert "\\bcuriosity" not in output


def test_danger_word_boundary(tmp_path):
    """gen_danger wraps word_boundary:true regexes with \\b and leaves false ones bare."""
    result = subprocess.run(
        ["node", str(GENERATORS / "gen_danger.js")],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, result.stderr
    output = (
        REPO_ROOT / "build" / "danger-plugin-no-animal-violence" / "src" / "index.ts"
    ).read_text()
    # word_boundary:true
    assert r'"\\bguinea\\s+pig\\b"' in output
    # word_boundary:false — no \b prefix
    assert r'"curiosity\\s+killed\\s+the\\s+cat"' in output
    assert r'"\\bcuriosity' not in output
