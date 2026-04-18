#!/usr/bin/env python3
"""Open sync PRs against all downstream repos.

Environment variables required:
  GH_TOKEN       Fine-grained PAT with contents:write and pull_requests:write
  CANONICAL_SHA  Full SHA of the canonical commit
  SHORT_SHA      Short SHA for branch names
  DRY_RUN        'true' to skip push and PR creation
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = REPO_ROOT / "build"

SEMGREP_BUILD = "semgrep-rules-no-animal-violence/rules/"

DOWNSTREAM_REPOS = [
    {
        "repo": "Open-Paws/eslint-plugin-no-animal-violence",
        "branch": "main",
        "files": {
            "lib/rules/no-violent-language.js": (
                "eslint-plugin-no-animal-violence/lib/rules/no-violent-language.js"
            ),
        },
    },
    {
        "repo": "Open-Paws/semgrep-rules-no-animal-violence",
        "branch": "main",
        "files": {
            "rules/animal-violence-generic.yaml": f"{SEMGREP_BUILD}animal-violence-generic.yaml",
            "rules/animal-violence-python.yaml": f"{SEMGREP_BUILD}animal-violence-python.yaml",
            "rules/animal-violence-javascript.yaml": f"{SEMGREP_BUILD}animal-violence-javascript.yaml",
            "rules/animal-violence-go.yaml": f"{SEMGREP_BUILD}animal-violence-go.yaml",
        },
    },
    {
        "repo": "Open-Paws/vale-no-animal-violence",
        "branch": "main",
        "files": {
            "NoAnimalViolence/AnimalIdioms.yml": (
                "vale-no-animal-violence/NoAnimalViolence/AnimalIdioms.yml"
            ),
            "NoAnimalViolence/IndustryEuphemisms.yml": (
                "vale-no-animal-violence/NoAnimalViolence/IndustryEuphemisms.yml"
            ),
            "NoAnimalViolence/meta.json": "vale-no-animal-violence/NoAnimalViolence/meta.json",
        },
    },
    {
        "repo": "Open-Paws/no-animal-violence-pre-commit",
        "branch": "main",
        "files": {
            "no_animal_violence_check.py": "no-animal-violence-pre-commit/no_animal_violence_check.py",
        },
    },
    {
        "repo": "Open-Paws/no-animal-violence-action",
        "branch": "main",
        "files": {
            "action.yml": "no-animal-violence-action/action.yml",
        },
    },
    {
        "repo": "Open-Paws/reviewdog-no-animal-violence",
        "branch": "main",
        "files": {
            "action.yml": "reviewdog-no-animal-violence/action.yml",
        },
    },
    {
        "repo": "Open-Paws/danger-plugin-no-animal-violence",
        "branch": "main",
        "files": {
            "src/index.ts": "danger-plugin-no-animal-violence/src/index.ts",
        },
    },
    {
        "repo": "Open-Paws/vscode-no-animal-violence",
        "branch": "main",
        "files": {
            "extension.js": "vscode-no-animal-violence/extension.js",
        },
    },
    {
        "repo": "Open-Paws/alex-no-animal-violence",
        "branch": "main",
        "files": {
            "animal-violence.yml": "alex-no-animal-violence/animal-violence.yml",
            "industry-euphemisms.yml": "alex-no-animal-violence/industry-euphemisms.yml",
        },
    },
    {
        "repo": "Open-Paws/woke-no-animal-violence",
        "branch": "main",
        "files": {
            ".woke.yaml": "woke-no-animal-violence/.woke.yaml",
        },
    },
]


def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)


def close_superseded_prs(repo: str, new_branch: str, canonical_sha: str, gh_env: dict) -> None:
    """Close any open automated-sync PRs that are not the current sync branch."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list",
             "--repo", repo,
             "--label", "automated-sync",
             "--state", "open",
             "--json", "number,headRefName"],
            capture_output=True, text=True, env=gh_env, check=True,
        )
        prs = json.loads(result.stdout or "[]")
        for pr in prs:
            if pr["headRefName"] == new_branch:
                continue
            subprocess.run(
                ["gh", "pr", "close", str(pr["number"]),
                 "--repo", repo,
                 "--comment",
                 f"Superseded by {new_branch} (canonical {canonical_sha[:12]})."
                 " All changes from this PR are included in the newer sync."],
                env=gh_env, capture_output=True,
            )
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        pass  # Non-fatal: worst case the old PR stays open


def propagate_repo(config: dict, sync_branch: str, canonical_sha: str, dry_run: bool) -> dict:
    repo = config["repo"]
    base_branch = config["branch"]
    result = {"repo": repo, "status": "unknown", "pr_url": None, "error": None}

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            token = os.environ["GH_TOKEN"]
            clone_url = f"https://x-access-token:{token}@github.com/{repo}.git"
            run(["git", "clone", "--depth=1", "-b", base_branch, clone_url, tmpdir])

            changed = False
            for dest_path, build_rel in config["files"].items():
                src = BUILD_DIR / build_rel
                dst = Path(tmpdir) / dest_path
                if not src.exists():
                    result["status"] = "build_missing"
                    result["error"] = f"Build output missing: {src}"
                    return result
                dst.parent.mkdir(parents=True, exist_ok=True)
                new_content = src.read_text()
                if dst.exists() and dst.read_text() == new_content:
                    continue
                dst.write_text(new_content)
                changed = True

            if not changed:
                result["status"] = "no_changes"
                return result

            if dry_run:
                result["status"] = "dry_run"
                return result

            gh_env = {**os.environ, "GH_TOKEN": token}
            close_superseded_prs(repo, sync_branch, canonical_sha, gh_env)

            run(["git", "checkout", "-b", sync_branch], cwd=tmpdir)
            run(["git", "config", "user.email", "sync-bot@openpaws.ai"], cwd=tmpdir)
            run(["git", "config", "user.name", "Open Paws Sync Bot"], cwd=tmpdir)
            run(["git", "add", "-A"], cwd=tmpdir)
            commit_msg = (
                f"sync: regenerate from canonical {canonical_sha[:12]}\n\n"
                f"Generated by propagate.yml in Open-Paws/no-animal-violence@{canonical_sha}"
            )
            run(["git", "commit", "-m", commit_msg], cwd=tmpdir)
            run(["git", "push", "origin", sync_branch], cwd=tmpdir)

            run(
                ["gh", "label", "create", "automated-sync",
                 "--repo", repo,
                 "--color", "0075ca",
                 "--description", "Automated rule sync from canonical repo",
                 "--force"],
                cwd=tmpdir,
                env=gh_env,
            )

            pr_title = f"sync: update rules from canonical {canonical_sha[:12]}"
            pr_body = (
                f"Automated sync from Open-Paws/no-animal-violence@{canonical_sha}.\n\n"
                "This PR was opened by the `propagate.yml` workflow. "
                "Rule definitions live in the canonical repo \u2014 edit there, not here.\n\n"
                "See [AUTOSYNC.md](.github/AUTOSYNC.md) for details."
            )
            pr_result = run(
                ["gh", "pr", "create",
                 "--repo", repo,
                 "--base", base_branch,
                 "--head", sync_branch,
                 "--title", pr_title,
                 "--body", pr_body,
                 "--label", "automated-sync"],
                cwd=tmpdir,
                env=gh_env,
            )
            result["pr_url"] = pr_result.stdout.strip()
            result["status"] = "pr_opened"

        except subprocess.CalledProcessError as exc:
            result["status"] = "error"
            result["error"] = exc.stderr[:500]

    return result


def main() -> int:
    canonical_sha = os.environ.get("CANONICAL_SHA", "unknown")
    short_sha = os.environ.get("SHORT_SHA", "unknown")
    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    sync_branch = f"sync/canonical-{short_sha}"

    results = []
    for config in DOWNSTREAM_REPOS:
        print(f"Processing {config['repo']}...", flush=True)
        r = propagate_repo(config, sync_branch, canonical_sha, dry_run)
        results.append(r)
        print(f"  -> {r['status']}" + (f": {r['pr_url']}" if r.get("pr_url") else ""))

    print("\n=== Propagation Summary ===")
    succeeded = [r for r in results if r["status"] in ("pr_opened", "no_changes", "dry_run")]
    failed = [r for r in results if r not in succeeded]

    for r in results:
        icon = "OK" if r["status"] in ("pr_opened", "no_changes", "dry_run") else "FAIL"
        print(f"  [{icon}] {r['repo']}: {r['status']}")
        if r.get("pr_url"):
            print(f"      PR: {r['pr_url']}")
        if r.get("error"):
            print(f"      Error: {r['error']}")

    if failed:
        print(f"\n{len(failed)} repo(s) failed.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
