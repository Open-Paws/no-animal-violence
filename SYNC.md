# Sync Infrastructure

The `propagate.yml` workflow pushes generated rule files to all 8 downstream repos and opens PRs.

## Auth setup

The workflow uses a fine-grained PAT stored as `SYNC_TOKEN` in this repo's secrets.

**Required permissions (fine-grained PAT):**
- Repository access: all 9 repos (this one + 8 downstream)
- Contents: Read and Write
- Pull requests: Read and Write
- Metadata: Read (automatic)

**Setup:**
1. Go to GitHub Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens
2. Create token with the permissions above for all 9 repos
3. Add as `SYNC_TOKEN` secret in this repo's settings

**Tradeoff vs GitHub App:**
A GitHub App would be cleaner (no expiry, scoped to org, audit trail) but requires registering an App and managing private keys. The PAT approach requires manual rotation (~annually). Document PAT expiry date in a comment in `propagate.yml` when created.

## Downstream repos

| Repo | Branch | Generated files |
|------|--------|----------------|
| eslint-plugin-no-animal-violence | main | `lib/rules/no-violent-language.js` |
| semgrep-rules-no-animal-violence | master | `rules/animal-violence-*.yaml` (4 files) |
| vale-no-animal-violence | main | `NoAnimalViolence/AnimalIdioms.yml`, `meta.json` |
| no-animal-violence-pre-commit | main | `no_animal_violence_check.py` |
| no-animal-violence-action | main | `action.yml` |
| reviewdog-no-animal-violence | main | `action.yml` |
| danger-plugin-no-animal-violence | main | `src/index.ts` |
| vscode-no-animal-violence | main | `extension.js` |

## How the push model works

1. Edit `rules.yaml` in this repo (the canonical source).
2. Run `python tools/generate_all.py` locally to preview output in `build/`.
3. Merge to `main`.
4. Trigger the `propagate.yml` workflow (manually, or enable the push trigger by uncommenting the `push:` block).
5. The workflow runs generators, then opens one PR per downstream repo with the updated files.
6. Maintainers of each downstream repo review and merge.

## Running locally

```bash
# Install dependencies
pip install pyyaml
npm install js-yaml

# Generate all outputs
python tools/generate_all.py

# Check for drift against local sibling repos
python tools/check_consistency.py

# Dry-run propagation (no push, no PR)
DRY_RUN=true CANONICAL_SHA=$(git rev-parse HEAD) SHORT_SHA=$(git rev-parse --short HEAD) GH_TOKEN=your_token python tools/propagate.py
```
