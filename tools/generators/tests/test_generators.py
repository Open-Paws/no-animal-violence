"""Golden-file tests for all generators."""
import re
import subprocess
import sys
from pathlib import Path

import pytest
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


CANONICAL_IGNORE_PATHS = [
    "scout.personas.yaml",
    "AGENTS.md",
    "CLAUDE.md",
    ".claude/rules/",
]


def _extract_woke_yaml_body(action_yml_text: str) -> dict:
    """Parse the embedded /tmp/.woke.yaml HEREDOC body out of a generated action.yml.

    The action.yml ships a composite step that writes /tmp/.woke.yaml via a
    bash heredoc:

        cat > /tmp/.woke.yaml << 'RULES'
        <yaml body, 8-space indented>
        RULES

    This helper extracts the body between the heredoc opener and the RULES
    sentinel, dedents the 8-space indent woke needs, and parses the result as
    YAML so tests can assert against the actual schema woke will see at runtime.
    Returns the parsed dict.
    """
    opener = "cat > /tmp/.woke.yaml << 'RULES'"
    assert opener in action_yml_text, (
        f"action.yml has no {opener!r} heredoc opener — generator structure changed"
    )
    after_opener = action_yml_text.split(opener, 1)[1]
    # The closing sentinel "RULES" sits on its own line, indented to match the
    # cat invocation. Match it as the first line that is exactly whitespace + RULES.
    body_lines: list[str] = []
    for line in after_opener.splitlines()[1:]:
        if line.strip() == "RULES":
            break
        body_lines.append(line)
    else:  # pragma: no cover - defensive
        raise AssertionError("RULES heredoc terminator not found after opener")
    # Dedent: the body is indented 8 spaces inside the composite step's run: |.
    # Use a permissive dedent so tests survive whitespace re-jiggering as long
    # as every body line shares a common leading indent.
    indent = min(
        (len(line) - len(line.lstrip(" ")) for line in body_lines if line.strip()),
        default=0,
    )
    dedented = "\n".join(line[indent:] for line in body_lines)
    parsed = yaml.safe_load(dedented)
    assert isinstance(parsed, dict), (
        f"woke YAML body did not parse as a mapping (got {type(parsed).__name__})"
    )
    return parsed


def test_build_woke_yaml_emits_ignore_files_as_list_of_strings():
    """_build_woke_yaml emits an `ignore_files` key whose value is a list of strings.

    Per woke source (pkg/config/config.go), `IgnoreFiles []string` is a list of
    inline gitignore-style PATTERNS — not a pointer to a .wokeignore file. The
    schema is `[]string`. A single-string value would silently fail at runtime
    (woke would treat it as one literal pattern), so this test asserts both
    presence and the list-of-strings shape.

    Mutation resistance:
      - Mutate `ignore_files: [...]` → omit key → fails on key check.
      - Mutate `ignore_files: [...]` → `ignore_files: ".wokeignore"` (the
        v1-plan bug) → fails on `isinstance(value, list)`.
      - Mutate any list element to non-string → fails on per-element type.
    """
    from gen_action import _build_woke_yaml

    rules = load_rules(FIXTURES / "rules_mini.yaml")
    rendered = _build_woke_yaml(rules, indent=0)
    parsed = yaml.safe_load(rendered)

    assert isinstance(parsed, dict), (
        f"_build_woke_yaml output did not parse as a mapping "
        f"(got {type(parsed).__name__})"
    )
    assert "ignore_files" in parsed, (
        "_build_woke_yaml output missing top-level 'ignore_files' key — "
        "woke will not skip canonical Open Paws paths"
    )
    ignore_files = parsed["ignore_files"]
    assert isinstance(ignore_files, list), (
        f"'ignore_files' must be a list (woke schema is []string), got "
        f"{type(ignore_files).__name__}: {ignore_files!r}"
    )
    assert len(ignore_files) >= 1, "'ignore_files' must not be empty"
    for entry in ignore_files:
        assert isinstance(entry, str), (
            f"every 'ignore_files' entry must be a string, got "
            f"{type(entry).__name__}: {entry!r}"
        )

    # Rules key must still be present alongside ignore_files (not replaced).
    assert "rules" in parsed, (
        "_build_woke_yaml dropped the 'rules' key when adding ignore_files — "
        "woke would have nothing to scan for"
    )
    assert isinstance(parsed["rules"], list) and len(parsed["rules"]) >= 1, (
        "'rules' key must remain a non-empty list"
    )


def test_build_woke_yaml_ignore_files_contains_canonical_paths():
    """_build_woke_yaml's `ignore_files` list contains every canonical path.

    Mutation resistance: dropping any one of the canonical paths flips this
    assertion. Substring matching is rejected — exact equality on the entry
    string catches drift like `scout.personas.yml` (wrong extension) or
    `.claude/rules` (missing trailing slash, which changes gitignore semantics).
    """
    from gen_action import _build_woke_yaml

    rules = load_rules(FIXTURES / "rules_mini.yaml")
    parsed = yaml.safe_load(_build_woke_yaml(rules, indent=0))
    ignore_files = parsed["ignore_files"]

    for canonical in CANONICAL_IGNORE_PATHS:
        assert canonical in ignore_files, (
            f"canonical Open Paws path {canonical!r} missing from "
            f"_build_woke_yaml ignore_files list (got {ignore_files!r})"
        )


def test_gen_action_woke_config_has_ignore_files(tmp_path):
    """Generated action.yml's embedded woke YAML carries ignore_files inline.

    End-to-end: generate the full action.yml, extract the /tmp/.woke.yaml
    HEREDOC body, parse it, and assert it has `ignore_files` shaped as a list
    of strings containing the canonical paths. This is the contract test —
    `_build_woke_yaml` is internal, but the embedded heredoc body is the
    runtime contract with woke 0.19.0.

    Mutation resistance via YAML parse, not substring match.
    """
    from gen_action import generate

    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "action.yml"
    generate(rules, output_path)
    content = output_path.read_text()

    # Outer action.yml schema must still parse.
    outer = yaml.safe_load(content)
    assert "runs" in outer and "steps" in outer["runs"], (
        "action.yml outer YAML structure broken"
    )

    woke_config = _extract_woke_yaml_body(content)
    assert "ignore_files" in woke_config, (
        "embedded /tmp/.woke.yaml heredoc body missing 'ignore_files' — "
        "woke will not skip fixture files at runtime"
    )
    ignore_files = woke_config["ignore_files"]
    assert isinstance(ignore_files, list), (
        f"embedded woke ignore_files must be a list, got {type(ignore_files).__name__}"
    )
    for canonical in CANONICAL_IGNORE_PATHS:
        assert canonical in ignore_files, (
            f"canonical path {canonical!r} missing from embedded woke "
            f"ignore_files list (got {ignore_files!r})"
        )


def test_gen_action_woke_config_includes_scout_personas_yaml(tmp_path):
    """Regression test for #65: scout.personas.yaml MUST be in ignore_files.

    The bug in #65 is specifically that `scout.personas.yaml` (a fixture file
    full of personas with phrases like 'guinea pig' on purpose, to exercise
    the rules) was being scanned by woke and flagged on every PR. The fix is
    that scout.personas.yaml ends up in the woke config's ignore_files list.

    This test fails specifically if a future refactor drops scout.personas.yaml
    from the canonical paths list — even if the other three paths remain.
    """
    from gen_action import generate

    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "action.yml"
    generate(rules, output_path)

    woke_config = _extract_woke_yaml_body(output_path.read_text())
    ignore_files = woke_config.get("ignore_files", [])
    assert "scout.personas.yaml" in ignore_files, (
        "scout.personas.yaml is the #65 regression case — it MUST appear in "
        f"the woke config ignore_files list. Got: {ignore_files!r}"
    )


def test_gen_action_woke_ignore_patterns_match_fixture_files(tmp_path):
    """Integration test: emitted ignore_files patterns actually skip fixture files.

    Simulates woke's runtime matching by feeding the generator's ignore_files
    list into a gitignore-pattern matcher (the same algorithm woke uses via
    go-git/go-git's gitignore parser, but in Python via `pathspec`). Builds a
    fixture repo with scout.personas.yaml plus a non-fixture file, and asserts
    that the patterns skip the fixture and do NOT skip the regular file.

    This catches the failure mode where ignore_files contains the right path
    strings but in a syntax that doesn't actually match (e.g. missing leading
    slash, wrong glob form, trailing-slash semantics drift).

    Mutation resistance: drop scout.personas.yaml from canonical paths -> the
    fixture file is no longer matched -> test fails. Replace bare filenames
    with absolute-only patterns -> bare files at deeper paths stop matching
    -> test fails on the nested case.
    """
    pathspec = pytest.importorskip("pathspec")  # noqa: F841

    from gen_action import _build_woke_yaml

    rules = load_rules(FIXTURES / "rules_mini.yaml")
    parsed = yaml.safe_load(_build_woke_yaml(rules, indent=0))
    ignore_patterns = parsed.get("ignore_files", [])
    assert isinstance(ignore_patterns, list) and ignore_patterns, (
        "ignore_files must be a non-empty list to test runtime matching"
    )

    import pathspec as _pathspec
    spec = _pathspec.PathSpec.from_lines(
        _pathspec.patterns.GitWildMatchPattern,
        ignore_patterns,
    )

    # Files that MUST match (be skipped by woke at runtime).
    must_match = [
        "scout.personas.yaml",          # at root — primary #65 case
        "AGENTS.md",
        "CLAUDE.md",
        ".claude/rules/some-rule.md",   # under canonical rules dir
        "subdir/scout.personas.yaml",   # bare-filename gitignore matches at any depth
    ]
    for path in must_match:
        assert spec.match_file(path), (
            f"emitted ignore_files patterns {ignore_patterns!r} do not match "
            f"{path!r} — woke would scan it at runtime and #65 reproduces"
        )

    # Files that MUST NOT match (regular code/docs that should still be scanned).
    must_not_match = [
        "src/main.py",
        "README.md",
        "docs/index.md",
        "tools/generators/gen_action.py",
    ]
    for path in must_not_match:
        assert not spec.match_file(path), (
            f"emitted ignore_files patterns {ignore_patterns!r} unexpectedly "
            f"match {path!r} — over-broad ignore would silence real findings"
        )


def test_gen_action_static_footer_drops_wokeignore_injection_step(tmp_path):
    """Plan v2 drops the never-propagated `.wokeignore` injection step.

    Path A inlines the canonical paths into the woke YAML config's
    `ignore_files:` key. The shell step that mutated consumer `.wokeignore`
    files (a) never propagated to the deployed action.yml, and (b) is
    redundant under Path A. Plan v2 explicitly removes it.

    This test asserts the artifacts of that step are gone from the generated
    action.yml. It fails on the current codebase (the step is still there)
    and goes green when STAGE 7 deletes the step from STATIC_FOOTER.

    Mutation resistance: any of the three step artifacts (step name, sentinel
    comment, append-to-.wokeignore command) coming back trips the test.
    """
    from gen_action import generate

    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "action.yml"
    generate(rules, output_path)
    content = output_path.read_text()

    # Outer schema still valid (the deletion mustn't break the action).
    data = yaml.safe_load(content)
    assert "runs" in data and "steps" in data["runs"], (
        "action.yml outer YAML structure broken after STATIC_FOOTER edit"
    )

    forbidden_artifacts = [
        # The composite-step name.
        "Inject canonical Open Paws paths into .wokeignore",
        # The idempotency sentinel comment line.
        "# no-animal-violence-action: canonical paths",
        # The mutation command — appending to consumer .wokeignore.
        ">> .wokeignore",
    ]
    for artifact in forbidden_artifacts:
        assert artifact not in content, (
            f"STATIC_FOOTER still contains {artifact!r} — plan v2 removes the "
            "wokeignore-injection step entirely (canonical paths now live in "
            "the woke YAML ignore_files key, not in consumer .wokeignore)"
        )




def test_gen_action_woke_command_present(tmp_path):
    """gen_action output contains the woke --exit-1-on-failure invocation.

    Regression guard: if STATIC_FOOTER loses the woke invocation, this fails.
    This test is GREEN against the current codebase — it guards against future
    regression where the footer is refactored and the woke call is accidentally
    dropped.
    """
    from gen_action import generate

    rules = load_rules(FIXTURES / "rules_mini.yaml")
    output_path = tmp_path / "action.yml"
    generate(rules, output_path)
    content = output_path.read_text()

    # Structural guard: output must be valid action YAML
    data = yaml.safe_load(content)
    assert "runs" in data, "action.yml top-level 'runs' key missing — YAML structure broken"

    # The woke invocation must be present
    assert "woke --exit-1-on-failure" in content, (
        "woke --exit-1-on-failure not found in generated action.yml — "
        "STATIC_FOOTER may have lost the woke invocation"
    )
