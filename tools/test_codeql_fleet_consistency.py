#!/usr/bin/env python3
"""Fleet-wide CodeQL CI consistency tests for issue #62.

This test module locks in the post-fix shape of CodeQL CI across the four
NAV-tooling repos covered by Open-Paws/no-animal-violence#62:

    - Open-Paws/vale-no-animal-violence            (Action/shim wrapper)
    - Open-Paws/no-animal-violence-action          (Action/shim wrapper)
    - Open-Paws/no-animal-violence-pre-commit      (Tooling/plugin library)
    - Open-Paws/semgrep-rules-no-animal-violence   (Tooling/plugin library)

Authoritative source for what each repo should look like:
    $OP_CONTEXT_REPO/handbook/ci-cd.md (Repo Taxonomy + CodeQL Configuration
    Framework + Supply Chain Hardening sections).

The tests query the live GitHub API. They are intentionally NOT in the default
unit-test path — they cost a network round trip per repo and only make sense
against the live fleet state. They are guarded by the `RUN_FLEET_TESTS=1`
environment variable so the unit-test job in CI does not flake on transient
GitHub API issues, but they MUST be runnable on demand by the verifier and
adversarial stages.

To run locally:

    RUN_FLEET_TESTS=1 pytest tools/test_codeql_fleet_consistency.py -v

Default branch verification (plan-reviewer's STAGE 4 defect): the plan said
``branches: ["master"]`` for ``semgrep-rules-no-animal-violence`` per a stale
``repos.yaml`` row, but the live API reports ``main``. These tests assert the
live default branch, not the stale config. If a repo's default branch ever
flips upstream, these tests will catch it before the workflow file silently
stops triggering.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

FLEET = {
    "vale-no-animal-violence": {
        "taxonomy": "shim",
        "expected_workflow": False,
        "expected_default_setup": False,
    },
    "no-animal-violence-action": {
        "taxonomy": "shim",
        "expected_workflow": False,
        "expected_default_setup": False,
    },
    "no-animal-violence-pre-commit": {
        "taxonomy": "tooling",
        "expected_workflow": True,
        "expected_default_setup": False,
        "expected_languages": {"python"},
    },
    "semgrep-rules-no-animal-violence": {
        "taxonomy": "tooling",
        "expected_workflow": True,
        "expected_default_setup": False,
        "expected_languages": {"python"},
    },
}

WORKFLOW_PATH = ".github/workflows/codeql.yml"

# SHA-pin pattern per handbook ci-cd.md "Supply Chain Hardening":
#     - uses: actions/checkout@<40-hex-sha>  # v<semver>
# The inline semver comment is required so the pin is auditable without
# resolving the SHA. Own-org actions (Open-Paws/*) are NEVER SHA-pinned.
THIRD_PARTY_USES = re.compile(
    r"""^\s*-\s*uses:\s*
        (?P<owner>[A-Za-z0-9_.-]+)/        # owner
        (?P<repo>[A-Za-z0-9_./-]+?)        # repo (may have nested path: codeql-action/init)
        @(?P<ref>[A-Za-z0-9_.-]+)          # ref (sha or tag)
        (?:\s*\#\s*(?P<comment>.*))?       # optional inline comment
        \s*$""",
    re.MULTILINE | re.VERBOSE,
)

SHA40 = re.compile(r"^[0-9a-f]{40}$")


# ---- helpers ----------------------------------------------------------------

run_fleet = pytest.mark.skipif(
    os.environ.get("RUN_FLEET_TESTS") != "1",
    reason=(
        "Fleet-wide CodeQL CI tests hit the live GitHub API. "
        "Set RUN_FLEET_TESTS=1 to enable. See module docstring."
    ),
)


def _gh_api(path: str) -> dict | list:
    """Run `gh api <path>` and return parsed JSON. Raises on non-zero exit
    EXCEPT for 404, which is returned as ``{"_status": 404}`` so callers can
    distinguish 'workflow file absent' from 'API broken'."""
    result = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    if "404" in result.stderr or "Not Found" in result.stderr:
        return {"_status": 404}
    raise RuntimeError(
        f"gh api {path} failed (exit {result.returncode}): "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def _get_workflow_content(repo: str) -> str | None:
    """Fetch the codeql.yml content from a repo's default branch. Returns
    None if the file does not exist."""
    payload = _gh_api(f"repos/Open-Paws/{repo}/contents/{WORKFLOW_PATH}")
    if isinstance(payload, dict) and payload.get("_status") == 404:
        return None
    if "content" not in payload:
        raise RuntimeError(
            f"repos/Open-Paws/{repo}/contents/{WORKFLOW_PATH} returned no "
            f"'content' field: {payload!r}"
        )
    import base64
    return base64.b64decode(payload["content"]).decode("utf-8")


def _list_workflow_paths(repo: str) -> list[str]:
    """Return the list of workflow `path` strings registered on the repo's
    Actions surface. Includes the synthetic `dynamic/github-code-scanning/codeql`
    entry when GitHub Default Setup is enabled."""
    payload = _gh_api(f"repos/Open-Paws/{repo}/actions/workflows")
    return [w["path"] for w in payload.get("workflows", [])]


def _default_branch(repo: str) -> str:
    """Return the live default branch for the repo. Authoritative over
    repos.yaml (which has been observed to drift)."""
    payload = _gh_api(f"repos/Open-Paws/{repo}")
    return payload["default_branch"]


# ---- contract tests: shape of the post-fix world ---------------------------

@run_fleet
@pytest.mark.parametrize(
    "repo",
    [r for r, m in FLEET.items() if m["expected_workflow"] is False],
)
def test_shim_repos_have_no_codeql_workflow_file(repo: str) -> None:
    """Action/shim repos must NOT have .github/workflows/codeql.yml.

    Per handbook ci-cd.md Repo Taxonomy: Action/shim wrappers have CodeQL=None.
    Today, vale-no-animal-violence ships a codeql.yml that conflicts with
    GitHub Default Setup and produces same-SHA flip-flop runs (see issue #62).
    The implementer must DELETE that file. no-animal-violence-action
    already has no codeql.yml; this test guards against regression.
    """
    content = _get_workflow_content(repo)
    assert content is None, (
        f"Open-Paws/{repo} must not ship .github/workflows/codeql.yml "
        f"(taxonomy: Action/shim wrapper, CodeQL=None per handbook ci-cd.md). "
        f"Live API returned {len(content)} bytes of YAML — file must be deleted."
    )


@run_fleet
@pytest.mark.parametrize(
    "repo",
    [r for r, m in FLEET.items() if m["expected_workflow"] is True],
)
def test_tooling_repos_have_canonical_codeql_workflow(repo: str) -> None:
    """Tooling/plugin library repos MUST ship a canonical codeql.yml.

    Asserts the structural properties handbook ci-cd.md mandates for
    Tooling/plugin library repos:
      - file exists at .github/workflows/codeql.yml
      - parses as YAML
      - top-level keys: name, on, permissions, jobs
      - on.push.branches and on.pull_request.branches both contain the
        repo's LIVE default branch (NOT a hardcoded value from repos.yaml)
      - exactly one job named 'analyze'
      - job runs on ubuntu-latest
      - language matrix matches the repo's actual content
      - init step declares queries: security-extended (handbook mandate;
        default-setup cannot do this, which is why those repos exist)
      - permissions block grants security-events: write
    """
    content = _get_workflow_content(repo)
    assert content is not None, (
        f"Open-Paws/{repo} (taxonomy: Tooling/plugin library) must ship "
        f"a custom .github/workflows/codeql.yml per handbook ci-cd.md. "
        f"Default Setup is forbidden because it cannot run "
        f"`security-extended` queries that tooling-library code requires."
    )

    data = yaml.safe_load(content)
    assert isinstance(data, dict), f"{repo}: codeql.yml must parse as a YAML mapping"

    for top_key in ("name", "on", "permissions", "jobs"):
        # YAML's `on:` key is parsed as boolean True by PyYAML; accept either.
        if top_key == "on":
            assert "on" in data or True in data, (
                f"{repo}: codeql.yml missing top-level `on:` key"
            )
            continue
        assert top_key in data, (
            f"{repo}: codeql.yml missing top-level `{top_key}:` key "
            f"(canonical skeleton requires name/on/permissions/jobs)"
        )

    on_block = data.get("on") or data.get(True)
    assert isinstance(on_block, dict), (
        f"{repo}: `on:` must be a mapping with push/pull_request/schedule keys"
    )

    live_branch = _default_branch(repo)
    for trigger in ("push", "pull_request"):
        trigger_block = on_block.get(trigger)
        assert isinstance(trigger_block, dict), (
            f"{repo}: `on.{trigger}` missing or not a mapping"
        )
        branches = trigger_block.get("branches")
        assert branches and live_branch in branches, (
            f"{repo}: `on.{trigger}.branches` must include the live default "
            f"branch '{live_branch}'. Got {branches!r}. "
            f"NOTE: repos.yaml may say 'master' for semgrep-rules — that is "
            f"stale; the live API is authoritative (STAGE 4 plan-reviewer "
            f"defect)."
        )

    # Permissions: security-events: write is mandatory for SARIF upload
    perms = data.get("permissions", {})
    assert perms.get("security-events") == "write", (
        f"{repo}: permissions.security-events must be 'write' for SARIF upload"
    )

    # Jobs: exactly one 'analyze' job
    jobs = data.get("jobs", {})
    assert "analyze" in jobs, (
        f"{repo}: must define a job named 'analyze' (canonical skeleton)"
    )
    analyze = jobs["analyze"]
    assert analyze.get("runs-on") == "ubuntu-latest", (
        f"{repo}: analyze.runs-on must be 'ubuntu-latest'"
    )

    # Language matrix
    expected_languages = FLEET[repo]["expected_languages"]
    matrix = analyze.get("strategy", {}).get("matrix", {})
    languages = set(matrix.get("language", []))
    assert languages == expected_languages, (
        f"{repo}: matrix.language must equal {expected_languages!r} "
        f"(determined by `git ls-files | grep extensions` per "
        f"handbook ci-cd.md Q1). Got {languages!r}."
    )

    # security-extended queries (handbook mandate for tooling repos)
    init_step = next(
        (
            s for s in analyze.get("steps", [])
            if isinstance(s, dict) and "init" in str(s.get("uses", ""))
        ),
        None,
    )
    assert init_step is not None, (
        f"{repo}: missing github/codeql-action/init step"
    )
    queries = init_step.get("with", {}).get("queries", "")
    assert "security-extended" in queries, (
        f"{repo}: init step must declare `queries: security-extended` "
        f"(handbook ci-cd.md Q2: tooling/plugin libraries run in other "
        f"developers' environments and need the extended query pack). "
        f"Got queries={queries!r}."
    )


@run_fleet
@pytest.mark.parametrize(
    "repo",
    [r for r, m in FLEET.items() if m["expected_workflow"] is True],
)
def test_tooling_repos_sha_pin_third_party_actions(repo: str) -> None:
    """Per decisions.md 2026-04-19 + handbook ci-cd.md Supply Chain Hardening.

    Every third-party `uses:` reference (anything not under Open-Paws/) must
    be pinned to a 40-character commit SHA with an inline `# v<semver>`
    comment. Own-org actions (`Open-Paws/*`) must stay on floating major-
    version tags.

    Defends against the tj-actions/changed-files class of compromise
    (CVE-2025-30066, March 2025): a tag rewrite on a third-party repo would
    silently swap the action your workflow runs, but a SHA pin freezes it.
    """
    content = _get_workflow_content(repo)
    assert content is not None, (
        f"{repo}: codeql.yml absent (precondition for this test)"
    )

    third_party_uses = []
    own_org_uses = []
    for match in THIRD_PARTY_USES.finditer(content):
        owner = match.group("owner")
        ref = match.group("ref")
        comment = match.group("comment") or ""
        if owner == "Open-Paws":
            own_org_uses.append((match.group(0).strip(), ref, comment))
        else:
            third_party_uses.append((match.group(0).strip(), owner, ref, comment))

    assert third_party_uses, (
        f"{repo}: codeql.yml has zero third-party `uses:` references. "
        f"Canonical skeleton requires actions/checkout + "
        f"github/codeql-action/{{init,autobuild,analyze}} — at least 4. "
        f"This is a parser failure or a malformed workflow."
    )

    for raw, owner, ref, comment in third_party_uses:
        assert SHA40.match(ref), (
            f"{repo}: third-party action `{owner}/...@{ref}` is not "
            f"SHA-pinned. Run `pinact run --path .github/workflows/codeql.yml`. "
            f"Raw line: {raw!r}"
        )
        assert re.search(r"v\d", comment), (
            f"{repo}: third-party action `{owner}/...@{ref}` is SHA-pinned but "
            f"missing the inline `# v<semver>` comment required by "
            f"handbook ci-cd.md Supply Chain Hardening. Raw line: {raw!r}"
        )

    for raw, ref, _comment in own_org_uses:
        assert not SHA40.match(ref), (
            f"{repo}: Open-Paws/* action is SHA-pinned at {ref!r}. "
            f"Per handbook ci-cd.md, own-org actions stay on floating "
            f"major-version tags by design. Raw line: {raw!r}"
        )


@run_fleet
@pytest.mark.parametrize("repo", list(FLEET.keys()))
def test_no_default_setup_workflow_registered(repo: str) -> None:
    """GitHub Default Setup must be disabled on every fleet repo.

    When Default Setup is enabled, GitHub registers a synthetic workflow
    with path `dynamic/github-code-scanning/codeql` in the actions API.
    That synthetic workflow conflicts with any file-based codeql.yml and
    is the documented root cause of issue #62
    ('CodeQL analyses from advanced configurations cannot be processed
    when the default setup is enabled').

    The /code-scanning/default-setup endpoint requires admin:repo_hook
    scope which the bot lacks (verified 403). The workflows-listing
    endpoint exposes the same signal and IS reachable from the bot's
    token, so we test there.

    NOT_TESTABLE-by-bot escape hatch: if the operator has not yet
    completed the click-path follow-up to disable Default Setup, this
    test will fail. That is intentional — it is the gate that confirms
    the ops issue actually landed.
    """
    paths = _list_workflow_paths(repo)
    assert "dynamic/github-code-scanning/codeql" not in paths, (
        f"Open-Paws/{repo}: GitHub Default Setup is still enabled "
        f"(synthetic workflow `dynamic/github-code-scanning/codeql` "
        f"is registered). Disable via Settings -> Code security -> "
        f"Code scanning -> CodeQL -> Disable. This requires repo:admin; "
        f"the bot cannot do it. See follow-up [ops] issue from #62."
    )


# ---- regression tests: today's broken state, locked in ---------------------

@run_fleet
def test_regression_vale_codeql_currently_conflicts_with_default_setup() -> None:
    """Regression anchor for the active flake on vale-no-animal-violence.

    On 2026-04-26 (run id 24951224601) vale's PR CI emitted:
        ##[warning]Failed to upload a SARIF file ...
        Processing errors: CodeQL analyses from advanced configurations
        cannot be processed when the default setup is enabled

    Root cause: vale ships BOTH a file-based codeql.yml AND has Default
    Setup enabled. The fix per the plan is to delete the file (taxonomy:
    Action/shim, CodeQL=None) AND for the operator to disable Default
    Setup. After the fix, the dual-config never reappears.
    """
    paths = _list_workflow_paths("vale-no-animal-violence")
    has_file_workflow = ".github/workflows/codeql.yml" in paths
    has_default_setup = "dynamic/github-code-scanning/codeql" in paths

    assert not (has_file_workflow and has_default_setup), (
        "vale-no-animal-violence: dual-config CodeQL state still present "
        f"(file workflow={has_file_workflow}, default-setup="
        f"{has_default_setup}). This is the exact failure mode from "
        f"issue #62. Either delete the file workflow OR disable "
        f"default-setup; never both."
    )


@run_fleet
@pytest.mark.parametrize(
    "repo",
    ["no-animal-violence-pre-commit", "semgrep-rules-no-animal-violence"],
)
def test_regression_tooling_repos_default_setup_only_violates_handbook(
    repo: str,
) -> None:
    """Regression anchor for the silent-coverage-degradation failure mode.

    Before the fix, both tooling repos run CodeQL via Default Setup ONLY
    (no .github/workflows/codeql.yml). Default Setup uses the
    `security-and-quality` query pack, but handbook ci-cd.md mandates
    `security-extended` for tooling/plugin libraries (these repos run in
    other developers' CI environments and need the extended pack).

    The pre-fix state therefore satisfies 'CodeQL is running' but FAILS
    'CodeQL is running with the right query pack'. Without this test,
    a future regression that re-deletes the file workflow would silently
    re-enable the silent-degradation state.

    Post-fix: file workflow exists with security-extended, default-setup
    disabled, no dual-config conflict.
    """
    paths = _list_workflow_paths(repo)
    has_file_workflow = WORKFLOW_PATH in paths
    has_default_setup = "dynamic/github-code-scanning/codeql" in paths

    assert has_file_workflow, (
        f"{repo} (taxonomy: Tooling/plugin library) has no file-based "
        f"codeql.yml. Default Setup alone does not satisfy the handbook "
        f"ci-cd.md mandate of `security-extended` queries — it runs "
        f"`security-and-quality` only, which silently downgrades "
        f"coverage. Implementer must add the canonical workflow."
    )
    assert not has_default_setup, (
        f"{repo}: Default Setup must be disabled once the file workflow "
        f"is in place (otherwise dual-config conflict per #62 root cause)."
    )


# ---- contract: in-repo discoverability of fleet expectations ---------------

def test_fleet_membership_matches_propagate_downstream_list() -> None:
    """Cross-check: every fleet repo this test module asserts against MUST
    appear in tools/propagate.py's DOWNSTREAM_REPOS list.

    This is mutation-resistant against a future contributor renaming a
    fleet repo without updating the test list, or vice-versa. It runs
    WITHOUT network — it parses propagate.py directly.

    This is a pure-Python test (no `run_fleet` marker) so it runs in the
    default unit-test job and catches drift cheaply.
    """
    propagate = (
        Path(__file__).resolve().parent / "propagate.py"
    ).read_text()
    fleet_repos_in_propagate = set(
        re.findall(r'"repo":\s*"Open-Paws/([\w-]+)"', propagate)
    )
    missing = set(FLEET.keys()) - fleet_repos_in_propagate
    assert not missing, (
        f"Fleet repos asserted in this test module but absent from "
        f"tools/propagate.py DOWNSTREAM_REPOS: {sorted(missing)}. "
        f"Either add them to propagate.py or remove from FLEET above. "
        f"Drift here means the generator suite and the CodeQL fleet "
        f"are out of sync."
    )


def test_fleet_taxonomy_matches_handbook_ci_cd_classifications() -> None:
    """Pure-Python sanity check: the FLEET dict's taxonomy field matches
    the classifications used in the plan for issue #62.

    This is a self-documentation test. If a future contributor edits FLEET
    to flip vale -> 'tooling' without re-reading the handbook, this catches
    it. The expected classifications come straight from
    handbook/ci-cd.md:11-18 Repo Taxonomy table.
    """
    expected = {
        "vale-no-animal-violence": "shim",
        "no-animal-violence-action": "shim",
        "no-animal-violence-pre-commit": "tooling",
        "semgrep-rules-no-animal-violence": "tooling",
    }
    actual = {repo: m["taxonomy"] for repo, m in FLEET.items()}
    assert actual == expected, (
        "FLEET taxonomy classifications drifted from the values verified "
        "by STAGE 4 plan-review against handbook/ci-cd.md:11-18. "
        f"expected={expected!r} actual={actual!r}. Re-read the handbook "
        "Repo Taxonomy table before changing this."
    )
