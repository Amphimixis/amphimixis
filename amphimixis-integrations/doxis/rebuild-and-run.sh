#!/usr/bin/env bash
# Usage:
#   rebuild-and-run.sh <list-file> [--limit N] [--from M] [--repo URL]
#                      [--config PATH] [--model PROVIDER/MODEL] [--no-build]
#                      [--extra-docker ARG]
set -euo pipefail

DOXIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$DOXIS_DIR/../.." && pwd)"
RUN="$DOXIS_DIR/run.sh"

AMPHIMIXIS_IMAGE="${AMPHIMIXIS_IMAGE:-amphimixis-opencode:latest}"
PROJECT_REPO=""
SKIP_BUILD=0
list_file=""
run_args=()

usage() {
  sed -n '2,5p' "$0"
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
    -*) echo "unknown option: $1" >&2; usage ;;
    *) list_file="$1"; shift ;;
  esac
done

[ -n "$list_file" ] || { echo "missing list file" >&2; usage; }

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }

if [ -n "$PROJECT_REPO" ]; then
  run_args=("--extra-docker" "-e" "--extra-docker" "PROJECT_REPO=$PROJECT_REPO" "${run_args[@]}")
fi

if [ "$SKIP_BUILD" -eq 0 ]; then
  echo "== building image ${AMPHIMIXIS_IMAGE}"
  docker build -f "$DOXIS_DIR/Dockerfile" -t "$AMPHIMIXIS_IMAGE" "$REPO_ROOT"
else
  echo "== skipping image build (--no-build)"
  docker image inspect "$AMPHIMIXIS_IMAGE" >/dev/null 2>&1 \
    || { echo "image not found: $AMPHIMIXIS_IMAGE (remove --no-build to build it)" >&2; exit 1; }
fi

echo "== running pipeline: $RUN ${run_args[*]}"
exec bash "$RUN" "$list_file" "${run_args[@]}"
