#!/usr/bin/env bash
# Usage:
#   rebuild-and-run.sh <list-file> [--limit N] [--skip M] [--repo URL]
#                      [--config PATH] [--model PROVIDER/MODEL] [--workdir DIR]
#                      [--no-build] [--no-run] [--extra-docker ARG]
set -euo pipefail

DOXIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DOXIS_DIR/../.." && pwd)"
RUN="$DOXIS_DIR/run.sh"

AMPHIMIXIS_IMAGE="${AMPHIMIXIS_IMAGE:-amphimixis-opencode:latest}"
PROJECT_REPO=""
PIPELINE_PROMPT=""
SKIP_BUILD=0
SKIP_RUN=0
list_file=""
run_args=()

usage() {
  sed -n '2,5p' "$0"
  exit 1
}
while [ "$#" -gt 0 ]; do
  case "$1" in
    --limit) run_args+=(--limit "${2:?}"); shift 2 ;;
    --skip) run_args+=(--skip "${2:?}"); shift 2 ;;
    --config) run_args+=(--config "${2:?}"); shift 2 ;;
    --model) run_args+=(--model "${2:?}"); shift 2 ;;
    --workdir) run_args+=(--workdir "${2:?}"); shift 2 ;;
    --extra-docker) run_args+=(--extra-docker "${2:?}"); shift 2 ;;
    --repo) PROJECT_REPO="${2:?}"; shift 2 ;;
    --prompt) PIPELINE_PROMPT="${2:?}"; shift 2 ;;
    --no-build) SKIP_BUILD=1; shift ;;
    --no-run) SKIP_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; [ "$#" -ge 1 ] && { list_file="$1"; shift; }; break ;;
    -*) echo "unknown option: $1" >&2; usage ;;
    *) list_file="$1"; shift ;;
  esac
done

[[ "$SKIP_RUN" -eq 0 && -z "$list_file" ]] && { echo "missing list file" >&2; usage; }

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }

if [ -n "$PROJECT_REPO" ]; then
  run_args=("--extra-docker" "-e" "--extra-docker" "PROJECT_REPO=$PROJECT_REPO" "${run_args[@]}")
fi

if [ -n "$PIPELINE_PROMPT" ]; then
  run_args=("--extra-docker" "-e" "--extra-docker" "PIPELINE_PROMPT=$PIPELINE_PROMPT" "${run_args[@]}")
fi

if [ "$SKIP_BUILD" -eq 0 ]; then
  echo "== building image ${AMPHIMIXIS_IMAGE}"
  docker build -f "$DOXIS_DIR/Dockerfile" -t "$AMPHIMIXIS_IMAGE" "$REPO_ROOT"
else
  echo "== skipping image build (--no-build)"
  docker image inspect "$AMPHIMIXIS_IMAGE" >/dev/null 2>&1 \
    || { echo "image not found: $AMPHIMIXIS_IMAGE (remove --no-build to build it)" >&2; exit 1; }
fi

if [ "$SKIP_RUN" -eq 0 ]; then
  echo "== running pipeline: $RUN ${run_args[*]}"
  exec bash "$RUN" "$list_file" "${run_args[@]}"
else
  echo "== skipping pipeline run (--no-run)"
fi
