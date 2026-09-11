#!/usr/bin/env bash
# 
# Applies the (Amphimixis opencode agent) pipeline to a list of projects,
# one container at a time: for each project from the list it
#   1. provisions input.yml from the per-project config (doxis/data/<project>.yml,
#      else the sample config doxis/data/sample.yml),
#   2. runs a fresh disposable container of the amphimixis-opencode image,
#      bind-mounting a fresh numbered work dir doxis/work/<project>_<i> as /work
#      (so all artifacts are written straight onto the host and kept there),
#   3. records the project in `state` and destroys the container. The image
#      layers (opencode + amixis + agents) survive, so the next project
#      starts from a clean slate.
#
# The work dir is never cleaned: it is named doxis/work/<project>_<i> where
# <i> is the ordinal equal to "already existing work dirs for that project + 1"
# (the first run creates doxis/work/<project>_1).
#
# Usage:
#   run.sh <list-file> [--limit N] [--from M] [--config PATH] [--model PROVIDER/MODEL]
set -euo pipefail

DOXIS_DIR="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
PIPELINE_DIR="$DOXIS_DIR/pipeline"

IMAGE="${AMPHIMIXIS_IMAGE:-amphimixis-opencode:latest}"
CONTAINER_NAME="${AMPHIMIXIS_CONTAINER_NAME:-amphimixis-worker}"
EXTRA_DOCKER_ARGS=()
list_file=""
limit=""
from="0"
config_file=""
model=""

usage() {
  sed -n '18,19p' "$0"
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --limit) limit="${2:?}"; shift 2 ;;
    --from) from="${2:?}"; shift 2 ;;
    --config) config_file="${2:?}"; shift 2 ;;
    --model) model="${2:?}"; shift 2 ;;
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

[ -n "$config_file" ] || config_file=""
if [ -n "$config_file" ]; then
  [ -f "$config_file" ] || { echo "config file not found: $config_file" >&2; exit 1; }
  config_file="$(readlink -f "$config_file")"
fi

parse_args=("$list_file")
[ -n "$limit" ] && parse_args+=(--limit "$limit")
parse_args+=(--from "$from")
mapfile -t projects < <("$PIPELINE_DIR/parse_list.sh" "${parse_args[@]}")

mkdir -p "$DOXIS_DIR/work"
touch "$DOXIS_DIR/state"

next_work_dir() {
  local project="$1"
  local i=1
  while [ -e "$DOXIS_DIR/work/${project}_${i}" ]; do
    i=$((i + 1))
  done
  printf '%s' "$DOXIS_DIR/work/${project}_${i}"
}

for project in "${projects[@]}"; do
  [ -n "$project" ] || continue
  if grep -qxF "$project" "$DOXIS_DIR/state"; then
    echo "== $project: already processed, skipping"
    continue
  fi

  work_dir="$(next_work_dir "$project")"
  mkdir -p "$work_dir"
  echo "== $(date '+%F %T') pipeline: $project -> $(basename "$work_dir") =="

  data_file="$DOXIS_DIR/data/$project.yml"
  [ -f "$data_file" ] || data_file="$DOXIS_DIR/data/$project.yaml"
  [ -f "$data_file" ] || data_file="$DOXIS_DIR/data/sample.yml"
  [ -f "$data_file" ] || { echo "  no data file or sample.yml, skipping $project"; continue; }
  cp "$data_file" "$work_dir/input.yml"

  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker_args=(
    --name "$CONTAINER_NAME"
    --rm
    --cap-add SYS_ADMIN
    -e "PROJECT_NAME=$project"
    -e "PUID=$(id -u)"
    -e "PGID=$(id -g)"
  )
  if [ -n "$model" ]; then
    docker_args+=(-e "MODEL=$model")
  fi
  if [ -n "$config_file" ]; then
    docker_args+=(-e "OPENCODE_CONFIG=/etc/opencode/opencode.json")
    docker_args+=(-v "$config_file:/etc/opencode/opencode.json:ro")
  fi
  docker_args+=(-v "$work_dir:/work")
  docker_args+=("${EXTRA_DOCKER_ARGS[@]}")
  docker_args+=("$IMAGE")

  set +e
  docker run "${docker_args[@]}" > "$work_dir/pipeline.log" 2>&1
  rc=$?
  set -e

  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

  echo "  container exit: $rc"
  if [ "$rc" -ne 0 ]; then
    echo "  docker run failed for $project (rc=$rc); log: $work_dir/pipeline.log"
  fi

  if compgen -G "$work_dir/*report.md" >/dev/null ; then
    echo "$project" >> "$DOXIS_DIR/state"
    echo "== $project: DONE, artifacts in $work_dir"
  else
    echo "== $project: FAILED (no report)"
  fi
done

echo "== finished. state file: $DOXIS_DIR/state (processed: $(grep -c . "$DOXIS_DIR/state"))"
echo "   project artifacts: $work_dir"
