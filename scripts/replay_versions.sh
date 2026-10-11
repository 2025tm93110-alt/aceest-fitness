#!/usr/bin/env bash
# Replays the legacy ACEest versions as individual commits + tags (one per version).
#
# Usage:  bash scripts/replay_versions.sh <folder-with-your-10-version-files> [rollback-list]
# e.g.    bash scripts/replay_versions.sh ~/Downloads/aceest "1.1.2"
#
# Each version is committed as legacy/ACEest_Fitness.py and tagged vX.Y.Z.
# Versions listed in [rollback-list] are tagged, then reverted with `git revert`,
# so history shows the defective release AND the rollback. Commit dates are real (not faked).
set -euo pipefail
SRC="${1:?give the folder containing the version files}"
ROLLBACK=" ${2:-} "

# version  |  commit message
VERSIONS=(
"1.0|Static program viewer: workout and diet charts per program"
"1.1|Client profile form, calorie estimate, adherence slider"
"1.1.2|Multi-client table, CSV export, adherence bar chart"
"2.0.1|Persist clients and weekly progress in SQLite"
"2.1.2|Refactor DB layer and summary view"
"2.2.1|Add adherence progress chart (matplotlib)"
"2.2.4|Add height, goals, workout and body-metric logging, BMI"
"3.0.1|Release 3.0.1 (functionally identical to 2.2.4)"
"3.1.2|Add login, AI program generator, PDF export, membership expiry"
"3.2.4|Add notebook UI, embedded charts, role-based dashboard"
)

find_file() {  # match e.g. 1.1.2 against Aceestver1_1_2.py / Aceestver-1.1.2.py / ...
  local key="${1//./}"
  for f in "$SRC"/*.py; do
    local n; n="$(basename "$f" .py | sed 's/^Aceestver//' | tr -d '._-')"
    [ "$n" = "$key" ] && { echo "$f"; return; }
  done
  echo "ERROR: no file found for version $1 in $SRC" >&2; exit 1
}

mkdir -p legacy
for entry in "${VERSIONS[@]}"; do
  v="${entry%%|*}"; msg="${entry#*|}"
  find_file "$v" >/dev/null
done  # fail early if any file is missing

for entry in "${VERSIONS[@]}"; do
  v="${entry%%|*}"; msg="${entry#*|}"
  tr -d '\r' < "$(find_file "$v")" > legacy/ACEest_Fitness.py
  git add legacy/ACEest_Fitness.py
  git commit -qm "feat(v$v): $msg"
  git tag -f "v$v" >/dev/null
  echo "committed + tagged v$v"
  if [[ "$ROLLBACK" == *" $v "* ]]; then
    git revert --no-edit HEAD >/dev/null
    git commit -q --amend -m "revert(v$v): roll back v$v to previous stable version"
    echo "  ↳ rolled back v$v"
  fi
done
git log --oneline
