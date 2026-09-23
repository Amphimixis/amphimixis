#!/usr/bin/env bash
#
# Single entrypoint of the dockerized Amphimixis pipeline. Builds the
# amphimixis-opencode image (unless --no-build) and then runs the pipeline
# over a project list via the internal pipeline/run.sh.
#
# Usage:
#   rebuild-and-run.sh <list-file> [--limit N] [--from M] [--repo URL]
#                      [--config PATH] [--model PROVIDER/MODEL] [--no-build]
#                      [--extra-docker ARG]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUN="$SCRIPT_DIR/pipeline/run.sh"

AMPHIMIXIS_IMAGE="${AMPHIMIXIS_IMAGE:-amphimixis-opencode:latest}"
PROJECT_REPO=""
SKIP_BUILD=0
list_file=""
run_args=()

usage() {
  sed -n '7,10p' "$0"
  exit 1
}

usage_err() {
  sed -n '7, 10p' "$0"
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --limit) run_args+=(--limit "${2:?}"); shift 2 ;;
    --from) run_args+=(--from "${2:?}"); shift 2 ;;
    --config) run_args+=(--config "${2:?}"); shift 2 ;;
    --model) run_args+=(--model "${2:?}"); shift 2 ;;
    --extra-docker) run_args+=(--extra-docker "${2:?}"); shift 2 ;;
    --repo) PROJECT_REPO="${2:?}"; shift 2 ;;
    --no-build) SKIP_BUILD=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; [ "$#" -ge 1 ] && { list_file="$1"; shift; }; break ;;
    -*) echo "unknown option: $1" >&2; usage_err ;;
    *) list_file="$1"; shift ;;
  esac
done

[ -n "$list_file" ] || { echo "missing list file" >&2; usage_err; }

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }

if [ -n "$PROJECT_REPO" ]; then
  run_args=("--extra-docker" "-e" "--extra-docker" "PROJECT_REPO=$PROJECT_REPO" "${run_args[@]}")
fi

if [ "$SKIP_BUILD" -eq 0 ]; then
  echo "== building image ${AMPHIMIXIS_IMAGE}"
  docker build -f "$SCRIPT_DIR/Dockerfile" -t "$AMPHIMIXIS_IMAGE" "$REPO_ROOT"
else
  echo "== skipping image build (--no-build)"
  docker image inspect "$AMPHIMIXIS_IMAGE" >/dev/null 2>&1 \
    || { echo "image not found: $AMPHIMIXIS_IMAGE (remove --no-build to build it)" >&2; exit 1; }
fi

echo "== running pipeline: $RUN ${run_args[*]}"
exec bash "$RUN" "$list_file" "${run_args[@]}"
