# Version Compatibility Matrix

This document tracks which version of each downstream tool is compatible with each version of the core rule set in this repository.

A stale tool silently misses new violations. Use `scripts/check_versions.sh` to detect drift automatically.

## Versioning Policy

| Increment | Meaning | Effect on suppressions |
|-----------|---------|----------------------|
| **Patch** (x.y.**Z**) | New rules added | No existing suppressions break |
| **Minor** (x.**Y**.0) | Rule text or IDs changed | Existing suppressions may stop matching |
| **Major** (**X**.0.0) | Rule format changed | Full re-validation required for all consumers |

**Consumers must upgrade to at least the minimum compatible version shown below.** Being more than one minor version behind means you are silently missing violation categories.

## Compatibility Matrix

| Core Rules | ESLint Plugin | VS Code Extension | Semgrep Rules | Vale Package | Pre-commit Hook | GitHub Action | Reviewdog Runner | Danger Plugin |
|-----------|--------------|-------------------|---------------|--------------|-----------------|---------------|------------------|---------------|
| 0.1.x | ≥ 0.1.0 | ≥ 0.1.0 | ≥ 0.1.0 | ≥ 0.1.0 | ≥ 0.1.0 | ≥ 0.1.0 | ≥ 0.1.0 | ≥ 0.1.0 |

> **Note:** No tool repos have published a tagged release yet. All tools are at version `0.1.0` (from `package.json` / `setup.py`). This matrix will be updated as tagged releases are published. See [Releasing](#releasing) below.

## How to Check Your Installed Versions

Run one command per tool to see what you currently have:

```bash
# ESLint plugin
npm list eslint-plugin-no-animal-violence 2>/dev/null | grep eslint-plugin-no-animal-violence

# VS Code extension (requires vsce or check the Extensions panel)
code --list-extensions | grep no-animal-violence

# Semgrep rules (pinned via git or semgrep registry)
# If cloned locally:
git -C path/to/semgrep-rules-no-animal-violence describe --tags 2>/dev/null || echo "no tags"

# Vale package
vale ls-config 2>/dev/null | grep -i "no-animal-violence\|speciesism" || echo "check .vale.ini"

# Pre-commit hook (installed via pip)
pip show no-animal-violence-pre-commit 2>/dev/null | grep Version

# GitHub Action — check your workflow file
grep -r "Open-Paws/no-animal-violence-action" .github/workflows/

# Reviewdog runner — check your workflow file
grep -r "Open-Paws/reviewdog-no-animal-violence" .github/workflows/

# Danger plugin
npm list danger-plugin-no-animal-violence 2>/dev/null | grep danger-plugin-no-animal-violence
```

Or run everything at once:

```bash
./scripts/check_versions.sh
```

## How to Update All Tools

```bash
# ESLint plugin
npm install eslint-plugin-no-animal-violence@latest

# Danger plugin
npm install --save-dev danger-plugin-no-animal-violence@latest

# Pre-commit hook
pip install --upgrade no-animal-violence-pre-commit

# Vale package — update the Packages line in .vale.ini to pin a new tag:
# Packages = https://github.com/Open-Paws/vale-no-animal-violence/releases/latest/download/Speciesism.zip
vale sync

# VS Code extension — update from the Extensions panel or:
code --install-extension Open-Paws.no-animal-violence --force

# GitHub Action and Reviewdog runner — bump the `@` pin in your workflow files:
# uses: Open-Paws/no-animal-violence-action@v0.1.0  →  @vX.Y.Z
# uses: Open-Paws/reviewdog-no-animal-violence@v0.1.0  →  @vX.Y.Z

# Semgrep rules (if cloned locally)
git -C path/to/semgrep-rules-no-animal-violence pull --tags
```

## Releasing

When releasing a new version of this core rule set:

1. Tag this repo: `git tag vX.Y.Z && git push origin vX.Y.Z`
2. Update the compatibility matrix above in a PR against main
3. Open issues in each downstream tool repo to pull the new rules in
4. Once downstream tools release, fill in their minimum compatible version in the matrix

## Tool Repositories

| Tool | Repository | Purpose |
|------|-----------|---------|
| ESLint Plugin | [eslint-plugin-no-animal-violence](https://github.com/Open-Paws/eslint-plugin-no-animal-violence) | JS/TS linting |
| VS Code Extension | [vscode-no-animal-violence](https://github.com/Open-Paws/vscode-no-animal-violence) | Real-time editor detection |
| Semgrep Rules | [semgrep-rules-no-animal-violence](https://github.com/Open-Paws/semgrep-rules-no-animal-violence) | Multi-language static analysis |
| Vale Package | [vale-no-animal-violence](https://github.com/Open-Paws/vale-no-animal-violence) | Prose and documentation |
| Pre-commit Hook | [no-animal-violence-pre-commit](https://github.com/Open-Paws/no-animal-violence-pre-commit) | Blocks commits with violations |
| GitHub Action | [no-animal-violence-action](https://github.com/Open-Paws/no-animal-violence-action) | CI/CD PR scanning |
| Reviewdog Runner | [reviewdog-no-animal-violence](https://github.com/Open-Paws/reviewdog-no-animal-violence) | Inline PR annotations |
| Danger Plugin | [danger-plugin-no-animal-violence](https://github.com/Open-Paws/danger-plugin-no-animal-violence) | Danger.js PR review |
