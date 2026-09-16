#!/usr/bin/env bash
# 
# Regenerates the softened Docker agents, rebuilds the amphimixis-opencode
# image, then runs the dockerized pipeline over a project list.
#
# Usage:
#   rebuild-and-run.sh <list-file> [--limit N] [--from M] [--repo URL] [--extra-docker ARG]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOFTEN_AGENTS="$SCRIPT_DIR/pipeline/soften_agents.py"
RUN="$SCRIPT_DIR/pipeline/run.sh"

IMAGE="${AMPHIMIXIS_IMAGE:-amphimixis-opencode:latest}"
PROJECT_REPO=""
run_args=()

usage() {
  sed -n '2,7p' "$0"
  exit 0
}

usage_err() {
  sed -n '6,7p' "$0" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo) PROJECT_REPO="${2:?}"; shift 2 ;;
    -h|--help) usage ;;
    --) shift; run_args+=("$@"); break ;;
    -*) run_args+=("$1"); shift ;;
    *) run_args+=("$1"); shift ;;
  esac
done

list_file=""
i=0
while [ "$i" -lt "${#run_args[@]}" ]; do
  arg="${run_args[$i]}"
  case "$arg" in
    --limit|--from|--extra-docker) i=$((i + 2)); continue ;;
    -*) ;;
    *) list_file="$arg"; break ;;
  esac
  i=$((i + 1))
done
[ -n "$list_file" ] || { echo "missing list file" >&2; usage_err; }

if [ -n "$PROJECT_REPO" ]; then
  run_args=("--extra-docker" "-e" "--extra-docker" "PROJECT_REPO=$PROJECT_REPO" "${run_args[@]}")
fi

command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }

echo "== regenerating softened agents (doxis/agents-docker)"
python3 "$SOFTEN_AGENTS"

echo "== building image $IMAGE"
docker build -f "$SCRIPT_DIR/Dockerfile" -t "$IMAGE" "$REPO_ROOT"

echo "== running pipeline: $RUN ${run_args[*]}"
exec bash "$RUN" --image "$IMAGE" "${run_args[@]}"
