#!/usr/bin/env bash
# check_versions.sh — Verify that installed no-animal-violence tools are up to date.
#
# Checks currently-installed versions of each tool against the latest published
# releases on GitHub. Warns if any tool is more than one minor version behind.
#
# Usage: ./scripts/check_versions.sh [--json]
#
# Exit codes:
#   0  All tools are up to date (or not installed)
#   1  One or more installed tools are outdated
#   2  A required dependency (curl, jq) is missing

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RESET='\033[0m'

JSON_OUTPUT=false
if [[ "${1:-}" == "--json" ]]; then
  JSON_OUTPUT=true
fi

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: '$cmd' is required but not installed." >&2
    exit 2
  fi
}

require_cmd curl
require_cmd jq

# ---------------------------------------------------------------------------
# Version arithmetic
# ---------------------------------------------------------------------------

# Returns 0 if $1 >= $2 (semver, major.minor.patch)
version_gte() {
  local a="$1" b="$2"
  # Strip leading 'v'
  a="${a#v}"; b="${b#v}"
  local a_maj a_min a_pat b_maj b_min b_pat
  IFS='.' read -r a_maj a_min a_pat <<<"$a"
  IFS='.' read -r b_maj b_min b_pat <<<"$b"
  a_maj="${a_maj:-0}"; a_min="${a_min:-0}"; a_pat="${a_pat:-0}"
  b_maj="${b_maj:-0}"; b_min="${b_min:-0}"; b_pat="${b_pat:-0}"
  if   (( a_maj > b_maj )); then return 0
  elif (( a_maj < b_maj )); then return 1
  elif (( a_min > b_min )); then return 0
  elif (( a_min < b_min )); then return 1
  elif (( a_pat >= b_pat )); then return 0
  else return 1
  fi
}

# Returns 0 if installed version is more than one minor behind latest
more_than_one_minor_behind() {
  local installed="$1" latest="$2"
  installed="${installed#v}"; latest="${latest#v}"
  local i_maj i_min l_maj l_min
  IFS='.' read -r i_maj i_min _ <<<"$installed"
  IFS='.' read -r l_maj l_min _ <<<"$latest"
  i_maj="${i_maj:-0}"; i_min="${i_min:-0}"
  l_maj="${l_maj:-0}"; l_min="${l_min:-0}"
  if   (( i_maj < l_maj )); then return 0
  elif (( i_maj > l_maj )); then return 1
  elif (( l_min - i_min > 1 )); then return 0
  else return 1
  fi
}

# ---------------------------------------------------------------------------
# GitHub latest-release lookup (falls back to package.json on main)
# ---------------------------------------------------------------------------

github_latest() {
  local repo="$1"
  local tag
  tag=$(curl -sf "https://api.github.com/repos/Open-Paws/${repo}/releases/latest" \
    -H "Accept: application/vnd.github+json" \
    ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
    | jq -r '.tag_name // empty' 2>/dev/null) || true

  if [[ -z "$tag" ]]; then
    # No release published — fall back to version in package.json / setup.py on main
    local pkg_version
    pkg_version=$(curl -sf "https://api.github.com/repos/Open-Paws/${repo}/contents/package.json" \
      -H "Accept: application/vnd.github+json" \
      ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
      | jq -r '.content' 2>/dev/null | base64 -d 2>/dev/null | jq -r '.version // empty' 2>/dev/null) || true

    if [[ -z "$pkg_version" ]]; then
      pkg_version=$(curl -sf "https://api.github.com/repos/Open-Paws/${repo}/contents/setup.py" \
        -H "Accept: application/vnd.github+json" \
        ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
        | jq -r '.content' 2>/dev/null | base64 -d 2>/dev/null \
        | grep -oP "version\s*=\s*['\"]\\K[^'\"]*" | head -1) || true
    fi

    tag="${pkg_version:-unknown}"
  fi

  echo "$tag"
}

# ---------------------------------------------------------------------------
# Per-tool version detection
# ---------------------------------------------------------------------------

installed_eslint_plugin() {
  npm list eslint-plugin-no-animal-violence --depth=0 2>/dev/null \
    | grep -oP 'eslint-plugin-no-animal-violence@\K[^\s]+' | head -1 || true
}

installed_danger_plugin() {
  npm list danger-plugin-no-animal-violence --depth=0 2>/dev/null \
    | grep -oP 'danger-plugin-no-animal-violence@\K[^\s]+' | head -1 || true
}

installed_vscode_extension() {
  code --list-extensions --show-versions 2>/dev/null \
    | grep -i 'no-animal-violence' \
    | grep -oP '@\K[^\s]+' | head -1 || true
}

installed_pre_commit_hook() {
  pip show no-animal-violence-pre-commit 2>/dev/null \
    | grep -i '^Version:' | awk '{print $2}' || true
}

installed_semgrep_rules() {
  # Semgrep rules are typically used via a local clone or semgrep registry.
  # Check for a local clone by looking for the repo directory near CWD.
  local search_dirs=("." ".." "../semgrep-rules-no-animal-violence" "semgrep-rules-no-animal-violence")
  for d in "${search_dirs[@]}"; do
    if [[ -d "$d/.git" ]] && git -C "$d" remote -v 2>/dev/null | grep -q "semgrep-rules-no-animal-violence"; then
      git -C "$d" describe --tags 2>/dev/null | sed 's/-.*//' || true
      return
    fi
  done
  echo ""
}

installed_vale_package() {
  # Vale packages are not pip/npm — check the .vale.ini for the pinned URL tag.
  local ini_file
  ini_file=$(find . -maxdepth 3 -name ".vale.ini" 2>/dev/null | head -1)
  if [[ -n "$ini_file" ]]; then
    grep -oP 'no-animal-violence[^/]*/releases/download/\K[^/]+' "$ini_file" | head -1 \
      || grep -oP 'Speciesism/releases/download/\K[^/]+' "$ini_file" | head -1 \
      || echo ""
  fi
}

# ---------------------------------------------------------------------------
# Main check loop
# ---------------------------------------------------------------------------

declare -A INSTALLED_VERSIONS
declare -A LATEST_VERSIONS
declare -A STATUS  # "ok", "outdated", "not_installed", "unknown"

check_tool() {
  local label="$1"
  local repo="$2"
  local installed="$3"

  local latest
  latest=$(github_latest "$repo")
  LATEST_VERSIONS["$label"]="$latest"

  if [[ -z "$installed" ]]; then
    INSTALLED_VERSIONS["$label"]="not installed"
    STATUS["$label"]="not_installed"
    return
  fi

  INSTALLED_VERSIONS["$label"]="$installed"

  if [[ "$latest" == "unknown" ]]; then
    STATUS["$label"]="unknown"
    return
  fi

  if version_gte "$installed" "$latest"; then
    STATUS["$label"]="ok"
  elif more_than_one_minor_behind "$installed" "$latest"; then
    STATUS["$label"]="outdated"
  else
    STATUS["$label"]="warn"
  fi
}

check_tool "ESLint Plugin"      "eslint-plugin-no-animal-violence"  "$(installed_eslint_plugin)"
check_tool "VS Code Extension"  "vscode-no-animal-violence"         "$(installed_vscode_extension)"
check_tool "Semgrep Rules"      "semgrep-rules-no-animal-violence"  "$(installed_semgrep_rules)"
check_tool "Vale Package"       "vale-no-animal-violence"           "$(installed_vale_package)"
check_tool "Pre-commit Hook"    "no-animal-violence-pre-commit"     "$(installed_pre_commit_hook)"
check_tool "GitHub Action"      "no-animal-violence-action"         ""  # CI-only, no local install
check_tool "Reviewdog Runner"   "reviewdog-no-animal-violence"      ""  # CI-only, no local install
check_tool "Danger Plugin"      "danger-plugin-no-animal-violence"  "$(installed_danger_plugin)"

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

OUTDATED=0

if $JSON_OUTPUT; then
  # Build JSON directly from bash associative arrays using printf
  printf '{\n'
  TOOLS_JSON=("ESLint Plugin" "VS Code Extension" "Semgrep Rules" "Vale Package" "Pre-commit Hook" "GitHub Action" "Reviewdog Runner" "Danger Plugin")
  last_idx=$(( ${#TOOLS_JSON[@]} - 1 ))
  for idx in "${!TOOLS_JSON[@]}"; do
    label="${TOOLS_JSON[$idx]}"
    comma=$( (( idx < last_idx )) && echo ',' || echo '' )
    printf '  "%s": {"installed": "%s", "latest": "%s", "status": "%s"}%s\n' \
      "$label" \
      "${INSTALLED_VERSIONS[$label]:-}" \
      "${LATEST_VERSIONS[$label]:-}" \
      "${STATUS[$label]:-}" \
      "$comma"
  done
  printf '}\n'
else
  echo ""
  echo "no-animal-violence tool version check"
  echo "======================================"
  printf "%-22s %-18s %-18s %s\n" "Tool" "Installed" "Latest" "Status"
  printf "%-22s %-18s %-18s %s\n" "----" "---------" "------" "------"

  TOOLS=("ESLint Plugin" "VS Code Extension" "Semgrep Rules" "Vale Package" "Pre-commit Hook" "GitHub Action" "Reviewdog Runner" "Danger Plugin")

  for label in "${TOOLS[@]}"; do
    installed="${INSTALLED_VERSIONS[$label]}"
    latest="${LATEST_VERSIONS[$label]}"
    st="${STATUS[$label]}"

    case "$st" in
      ok)            status_str="${GREEN}up to date${RESET}" ;;
      warn)          status_str="${YELLOW}behind (< 1 minor)${RESET}" ;;
      outdated)      status_str="${RED}OUTDATED (> 1 minor behind)${RESET}"; OUTDATED=1 ;;
      not_installed) status_str="not installed" ;;
      *)             status_str="unknown" ;;
    esac

    printf "%-22s %-18s %-18s %b\n" "$label" "$installed" "$latest" "$status_str"
  done

  echo ""
  if (( OUTDATED > 0 )); then
    echo -e "${RED}One or more tools are outdated. Run the update commands in VERSIONS.md.${RESET}"
    exit 1
  else
    echo -e "${GREEN}All tools up to date.${RESET}"
    exit 0
  fi
fi
