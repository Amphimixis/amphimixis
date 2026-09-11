#!/usr/bin/env bash
# Usage: collect_artifacts.sh <project> [work_dir] [results_dir]
set -euo pipefail

project="${1:?usage: collect_artifacts.sh <project> [work_dir] [results_dir]}"
if [[ ! "$project" =~ ^[a-zA-Z0-9._-]+$ ]]; then
  echo "collect_artifacts: invalid project name: '$project'" >&2
  echo "  allowed characters: a-z A-Z 0-9 . _ -" >&2
  exit 1
fi
work_dir="${2:-$(dirname "$(dirname "$(readlink -f "$0")")")/work}"
results_dir="${3:-$(dirname "$(dirname "$(readlink -f "$0")")")/results}"

src="$work_dir/$project"
dst="$results_dir/$project"
if [ ! -d "$src" ]; then
  echo "collect_artifacts: no work dir for $project: $src" >&2
  exit 1
fi
mkdir -p "$dst"

for f in "$src/amphimixis-$project-report.md" \
         "$src/improvements.json" \
         "$src/input.yml" \
         "$src/pipeline.log"; do
  [ -f "$f" ] && cp -f "$f" "$dst/"
done

if [ -d "$src/cross-tables" ]; then
  mkdir -p "$dst/cross-tables"
  cp -f "$src"/cross-tables/CT-*.md "$dst/cross-tables/" 2>/dev/null || true
fi

(cd "$src" && find . -type f \( \
      -name "$project.json" \
      -o -name "$project.yaml" \
      -o -name "$project.yml" \
      -o -name "$project.pkl" \
      -o -name '*.scriptout' \
      -o -name '*.perfdata' \
      -o -name '*.tar.bz2' \
      -o -name 'build.log' \
      -o -name 'perf_stat*.txt' \
      -o -name 'time_run_*.txt' \
  \) -exec cp --parents {} "$(readlink -f "$dst")/" \; 2>/dev/null || true)

echo "collected artifacts for $project -> $dst"
[ -f "$dst/amphimixis-$project-report.md" ] || echo "  NOTE: amphimixis-$project-report.md not found"
