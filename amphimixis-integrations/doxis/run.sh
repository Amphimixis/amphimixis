#!/usr/bin/env bash
# Usage:
#   run.sh <list-file> [--limit N] [--skip M] [--config PATH] [--model PROVIDER/MODEL]
#                      [--workdir DIR]
set -euo pipefail

DOXIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE="${AMPHIMIXIS_IMAGE:-amphimixis-opencode:latest}"
CONTAINER_NAME="${AMPHIMIXIS_CONTAINER_NAME:-amphimixis-worker}"
EXTRA_DOCKER_ARGS=()
list_file=""
limit=""
skip="0"
config_file=""
model=""
workdir=""

usage() {
  sed -n '2,4p' "$0"
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --limit) limit="${2:?}"; shift 2 ;;
    --skip) skip="${2:?}"; shift 2 ;;
    --config) config_file="${2:?}"; shift 2 ;;
    --model) model="${2:?}"; shift 2 ;;
    --workdir) workdir="${2:?}"; shift 2 ;;
    --extra-docker) EXTRA_DOCKER_ARGS+=("$2"); shift 2 ;;
    -h|--help) usage ;;
    -*) echo "unknown option: $1" >&2; usage ;;
    *) list_file="$1"; shift ;;
  esac
done

[ -n "$list_file" ] || { echo "missing list file"; usage; }
[ -f "$list_file" ] || { echo "list file not found: $list_file" >&2; exit 1; }
[[ "$skip" =~ ^[0-9]+$ ]] || { echo "--skip must be a non-negative integer" >&2; exit 2; }
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

if [ -n "$workdir" ]; then
  [ -e "$workdir" ] && [ ! -d "$workdir" ] && { echo "workdir is not a directory: $workdir" >&2; exit 2; }
  mkdir -p "$workdir"
  workdir="$(readlink -f "$workdir")"
fi

mapfile -t projects < <(awk 'NF { print $1 }' "$list_file")

if [ "${#projects[@]}" -gt 0 ]; then
  if [ -n "$limit" ]; then
    projects=("${projects[@]:$skip:$limit}")
  elif [ "$skip" -gt 0 ]; then
    projects=("${projects[@]:$skip}")
  fi
fi

WORK_BASE="$DOXIS_DIR/work"
RESUME=0
if [ -n "$workdir" ]; then
  if [ "${#projects[@]}" -eq 1 ]; then
    RESUME=1
  else
    WORK_BASE="$workdir"
  fi
else
  mkdir -p "$WORK_BASE"
fi

touch "$DOXIS_DIR/state"

next_work_dir() {
  local project="$1"
  local i=1
  while [ -e "$WORK_BASE/${project}_${i}" ]; do
    i=$((i + 1))
  done
  printf '%s' "$WORK_BASE/${project}_${i}"
}

for project in "${projects[@]}"; do
  [ -n "$project" ] || continue
  if grep -qxF "$project" "$DOXIS_DIR/state"; then
    echo "== $project: already processed, skipping"
    continue
  fi

  project_dir=""
  resume_mode=0
  if [ "$RESUME" -eq 1 ]; then
    project_dir="$workdir"
    resume_mode=1
  else
    project_dir="$(next_work_dir "$project")"
    mkdir -p "$project_dir"
  fi
  echo "== $(date '+%F %T') pipeline: $project -> $project_dir =="

  data_file="$DOXIS_DIR/data/$project.yml"
  [ -f "$data_file" ] || data_file="$DOXIS_DIR/data/$project.yaml"
  [ -f "$data_file" ] || data_file="$DOXIS_DIR/data/sample.yml"
  [ -f "$data_file" ] || { echo "  no data file or sample.yml, skipping $project"; continue; }
  if [ "$resume_mode" -eq 1 ] && [ -f "$project_dir/input.yml" ]; then
    echo "  keeping existing input.yml (--workdir resume mode)"
  else
    cp "$data_file" "$project_dir/input.yml"
  fi

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
  docker_args+=(-v "$project_dir:/work")
  docker_args+=("${EXTRA_DOCKER_ARGS[@]}")
  docker_args+=("$IMAGE")

  trap 'docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true; exit 130' INT TERM
  
  set +e
  if [ "$resume_mode" -eq 1 ]; then
    echo "== $(date '+%F %T') resume run: $project -> $project_dir ==" >> "$project_dir/pipeline.log"
    docker run "${docker_args[@]}" 2>&1 | awk '{ print strftime("%Y-%m-%d %H:%M:%S"), $0; fflush() }' >> "$project_dir/pipeline.log"
  else
    docker run "${docker_args[@]}" 2>&1 | awk '{ print strftime("%Y-%m-%d %H:%M:%S"), $0; fflush() }' > "$project_dir/pipeline.log"
  fi
  rc=${PIPESTATUS[0]}
  set -e

  echo "  container exit: $rc"
  if [ "$rc" -ne 0 ]; then
    echo "  docker run failed for $project (rc=$rc); log: $project_dir/pipeline.log"
  fi

  if find "$project_dir" -type f -name '*report.md' -print -quit | grep -q .; then
    echo "$project" >> "$DOXIS_DIR/state"
    echo "== $project: DONE, artifacts in $project_dir"
  else
    echo "== $project: FAILED (no report)"
  fi
done

echo "== finished. state file: $DOXIS_DIR/state (processed: $(grep -c . "$DOXIS_DIR/state"))"
