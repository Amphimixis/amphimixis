#!/usr/bin/env bash
# Usage:
#   run.sh <list-file> [--limit N] [--from M] [--config PATH] [--model PROVIDER/MODEL]
set -euo pipefail

DOXIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE="${AMPHIMIXIS_IMAGE:-amphimixis-opencode:latest}"
CONTAINER_NAME="${AMPHIMIXIS_CONTAINER_NAME:-amphimixis-worker}"
EXTRA_DOCKER_ARGS=()
list_file=""
limit=""
from="0"
config_file=""
model=""

usage() {
  sed -n '2,3p' "$0"
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
[ -f "$list_file" ] || { echo "list file not found: $list_file" >&2; exit 1; }
[[ "$from" =~ ^[0-9]+$ ]] || { echo "--from must be a non-negative integer" >&2; exit 2; }
if [ -n "$limit" ]; then
  [[ "$limit" =~ ^[0-9]+$ ]] || { echo "--limit must be a non-negative integer" >&2; exit 2; }
fi

command -v docker >/dev/null 2>&1 || { echo "docker is required" >&2; exit 1; }
docker image inspect "$IMAGE" >/dev/null 2>&1 \
  || { echo "image not found: $IMAGE (build it: docker build -f $DOXIS_DIR/Dockerfile -t $IMAGE <repo-root> )" >&2; exit 1; }

if [ -n "$config_file" ]; then
  [ -f "$config_file" ] || { echo "config file not found: $config_file" >&2; exit 1; }
  config_file="$(readlink -f "$config_file")"
fi

mapfile -t projects < <(awk 'NF { print $1 }' "$list_file")

if [ "${#projects[@]}" -gt 0 ]; then
  if [ -n "$limit" ]; then
    projects=("${projects[@]:$from:$limit}")
  elif [ "$from" -gt 0 ]; then
    projects=("${projects[@]:$from}")
  fi
fi

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
  docker run "${docker_args[@]}" 2>&1 | awk '{ print strftime("%Y-%m-%d %H:%M:%S"), $0; fflush() }' > "$work_dir/pipeline.log"
  rc=${PIPESTATUS[0]}
  set -e

  trap 'docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true; exit 130' INT TERM

  echo "  container exit: $rc"
  if [ "$rc" -ne 0 ]; then
    echo "  docker run failed for $project (rc=$rc); log: $work_dir/pipeline.log"
  fi

  if find "$work_dir" -type f -name '*report.md' -print -quit | grep -q .; then
    echo "$project" >> "$DOXIS_DIR/state"
    echo "== $project: DONE, artifacts in $work_dir"
  else
    echo "== $project: FAILED (no report)"
  fi
done

echo "== finished. state file: $DOXIS_DIR/state (processed: $(grep -c . "$DOXIS_DIR/state"))"
