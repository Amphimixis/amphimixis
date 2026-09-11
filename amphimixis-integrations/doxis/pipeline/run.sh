#!/usr/bin/env bash
# 
# Applies the (Amphimixis opencode agent) pipeline to a list of projects,
# one container at a time: for each project from the list it
#   1. provisions input.yml from the per-project config (doxis/data/<project>.yml,
#      else the sample config doxis/data/sample.yml),
#   2. runs a fresh disposable container of the amphimixis-opencode image,
#      bind-mounting doxis/work/<project> as /work (so all artifacts are
#      written straight onto the host),
#   3. curates the artifacts into results/<project>,
#   4. records the project in `state` and destroys the container. The image
#      layers (opencode + amixis + agents) survive, so the next project
#      starts from a clean slate.
#
# Usage:
#   run.sh <list-file> [--limit N] [--from M] [--image TAG]
set -euo pipefail

DOXIS_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
PIPELINE_DIR="$DOXIS_DIR/pipeline"

IMAGE="${AMPHIMIXIS_IMAGE:-amphimixis-opencode:latest}"
CONTAINER_NAME="${AMPHIMIXIS_CONTAINER_NAME:-amphimixis-worker}"
EXTRA_DOCKER_ARGS=()
list_file=""
limit=""
from="0"

usage() {
  sed -n '16p' "$0"
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --limit) limit="${2:?}"; shift 2 ;;
    --from) from="${2:?}"; shift 2 ;;
    --image) IMAGE="${2:?}"; shift 2 ;;
    --extra-docker) EXTRA_DOCKER_ARGS+=("$2"); shift 2 ;;
    -h|--help) usage ;;
    -*) echo "unknown option: $1" >&2; usage ;;
    *) list_file="$1"; shift ;;
  esac
done

[ -n "$list_file" ] || { echo "missing list file"; usage; }

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
docker image inspect "$IMAGE" >/dev/null 2>&1 \
  || { echo "image not found: $IMAGE (build it: docker build -f $DOXIS_DIR/Dockerfile -t $IMAGE <repo-root> )" >&2; exit 1; }

mapfile -t projects < <("$PIPELINE_DIR/parse_list.sh" "$list_file" $( [ -n "$limit" ] && echo --limit "$limit" ) --from "$from")

mkdir -p "$DOXIS_DIR/work" "$DOXIS_DIR/results"
touch "$DOXIS_DIR/state"

created_work=()
remove_work_dir() {
  local dir="$1"
  [ -e "$dir" ] || return 0
  if rm -rf -- "$dir" 2>/dev/null; then
    return 0
  fi

  echo "  $dir has root-owned files; removing via disposable container"
  docker run --rm --cap-add CAP_DAC_OVERRIDE --cap-add CAP_FOWNER --cap-add CAP_CHOWN --entrypoint /bin/rm \
    -v "$(dirname -- "$dir"):/parent:rw" \
    "$IMAGE" -rf -- "/parent/$(basename -- "$dir")" || true
  rm -rf -- "$dir" 2>/dev/null || true
}
cleanup_work() {
  if [ "${#created_work[@]}" -gt 0 ]; then
    echo "== cleaning this run's work dirs from doxis/work/ (containers ended)"
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    for dir in "${created_work[@]}"; do
      remove_work_dir "$dir"
    done
    mkdir -p "$DOXIS_DIR/work"
  fi
}
trap cleanup_work EXIT

for project in "${projects[@]}"; do
  [ -n "$project" ] || continue
  if grep -qxF "$project" "$DOXIS_DIR/state"; then
    echo "== $project: already processed, skipping"
    continue
  fi

  echo "== $(date '+%F %T') pipeline: $project =="
  remove_work_dir "$DOXIS_DIR/work/$project"
  mkdir -p "$DOXIS_DIR/work/$project" "$DOXIS_DIR/results/$project"

  data_file="$DOXIS_DIR/data/$project.yml"
  [ -f "$data_file" ] || data_file="$DOXIS_DIR/data/$project.yaml"
  [ -f "$data_file" ] || data_file="$DOXIS_DIR/data/sample.yml"
  [ -f "$data_file" ] || { echo "  no data file or sample.yml, skipping $project"; continue; }
  cp "$data_file" "$DOXIS_DIR/work/$project/input.yml"

  created_work+=("$DOXIS_DIR/work/$project")
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  set +e
  docker run --name "$CONTAINER_NAME" --rm \
      --cap-add SYS_ADMIN \
      -e PROJECT_NAME="$project" \
      -e PUID="$(id -u)" -e PGID="$(id -g)" \
      -v "$DOXIS_DIR/work/$project:/work" \
      ${EXTRA_DOCKER_ARGS[@]+"${EXTRA_DOCKER_ARGS[@]}"} \
      "$IMAGE" \
      > "$DOXIS_DIR/work/$project/pipeline.log" 2>&1
  rc=$?
  set -e

  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

  echo "  container exit: $rc"
  if [ "$rc" -ne 0 ]; then
    echo "  docker run failed for $project (rc=$rc); log: work/$project/pipeline.log"
  fi

  "$PIPELINE_DIR/collect_artifacts.sh" "$project" "$DOXIS_DIR/work" "$DOXIS_DIR/results" || true

  if [ -f "$DOXIS_DIR/work/$project/amphimixis-$project-report.md" ]; then
    echo "$project" >> "$DOXIS_DIR/state"
    echo "== $project: DONE, artifacts in results/$project"
  else
    echo "== $project: FAILED (no report); log: work/$project/pipeline.log"
  fi
done

echo "== finished. state file: $DOXIS_DIR/state (processed: $(grep -c . "$DOXIS_DIR/state"))"
echo "   curated project artifacts: $DOXIS_DIR/results/<project>"
