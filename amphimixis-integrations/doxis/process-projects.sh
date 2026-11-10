#!/usr/bin/env bash
# Usage:
#   process-projects.sh [<list-file>] [--limit N] [--skip M] [--config PATH] [--model PROVIDER/MODEL]
#                      [--workdir DIR | --resume DIR]
set -euo pipefail

DOXIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

IMAGE="${AMPHIMIXIS_IMAGE:-amphimixis-opencode:latest}"
CONTAINER_NAME="${AMPHIMIXIS_CONTAINER_NAME:-amphimixis-worker}"
EXTRA_DOCKER_ARGS=()
list_file=""
limit=""
skip=""
config_file=""
model=""
workdir=""
resume_dir=""

usage() {
  sed -n '2,4p' "$0"
  exit 1
}

load_resume_context() {
  local workspace="$1"
  local metadata
  if [ ! -d "$workspace" ] || [ ! -f "$workspace/pipeline.log" ] || [ ! -f "$workspace/input.yml" ]; then
    echo "--resume requires an existing workspace with pipeline.log and input.yml" >&2
    return 2
  fi

  metadata="$(sed -nE 's/^([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} )?\[entrypoint\] opencode: starting pipeline for ([[:alnum:]_.+-]+) \(model=([^()[:space:]]+)\)$/\2 \3/p' "$workspace/pipeline.log" | tail -n 1)"
  if [ -z "$metadata" ]; then
    echo "--resume: no valid project/model startup entry in $workspace/pipeline.log" >&2
    return 2
  fi
  read -r resume_project resume_model <<< "$metadata"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --limit) limit="${2:?}"; shift 2 ;;
    --skip) skip="${2:?}"; shift 2 ;;
    --config) config_file="${2:?}"; shift 2 ;;
    --model) model="${2:?}"; shift 2 ;;
    --resume) resume_dir="${2:?}"; shift 2 ;;
    --workdir) workdir="${2:?}"; shift 2 ;;
    --extra-docker) EXTRA_DOCKER_ARGS+=("$2"); shift 2 ;;
    -h|--help) usage ;;
    -*) echo "unknown option: $1" >&2; usage ;;
    *) list_file="$1"; shift ;;
  esac
done

if [ -n "$resume_dir" ]; then
  if [ -n "$list_file" ] || [ -n "$limit" ] || [ -n "$skip" ] || [ -n "$workdir" ]; then
    echo "--resume cannot be combined with a list file, --limit, --skip, or --workdir" >&2
    exit 2
  fi
  load_resume_context "$resume_dir"
  resume_dir="$(readlink -f "$resume_dir")"
  projects=("$resume_project")
  model="${model:-$resume_model}"
else
  [ -n "$list_file" ] || { echo "missing list file"; usage; }
  [ -f "$list_file" ] || { echo "list file not found: $list_file" >&2; exit 1; }
  skip="${skip:-0}"
  [[ "$skip" =~ ^[0-9]+$ ]] || { echo "--skip must be a non-negative integer" >&2; exit 2; }
  if [ -n "$limit" ]; then
    [[ "$limit" =~ ^[0-9]+$ ]] || { echo "--limit must be a non-negative integer" >&2; exit 2; }
  fi
  mapfile -t projects < <(awk 'NF { print $1 }' "$list_file")
  if [ "${#projects[@]}" -gt 0 ]; then
    if [ -n "$limit" ]; then
      projects=("${projects[@]:$skip:$limit}")
    elif [ "$skip" -gt 0 ]; then
      projects=("${projects[@]:$skip}")
    fi
  fi
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

WORK_BASE="${workdir:-$DOXIS_DIR/work}"

touch "$DOXIS_DIR/state"

next_work_dir() {
  local project="$1"
  local i=1
  while [ -e "$WORK_BASE/${project}_${i}" ]; do
    i=$((i + 1))
  done
  printf '%s' "$WORK_BASE/${project}_${i}"
}

ACTIVE_CONTAINER=""
DOCKER_PID=""
LOGGER_PID=""

cleanup_container() {
  [ -n "$ACTIVE_CONTAINER" ] || return 0
  docker stop --time 10 "$ACTIVE_CONTAINER" >/dev/null 2>&1 || true
  if ! docker rm -f "$ACTIVE_CONTAINER" >/dev/null 2>&1; then
    if docker container inspect "$ACTIVE_CONTAINER" >/dev/null 2>&1 \
      || ! docker info >/dev/null 2>&1; then
      echo "error: could not confirm removal of container $ACTIVE_CONTAINER" >&2
    fi
  fi
  ACTIVE_CONTAINER=""
}

cancel_run() {
  local status="$1"
  trap '' INT TERM
  if [ -n "${log_fd:-}" ]; then
    exec {log_fd}>&-
  fi
  cleanup_container
  for child in "$DOCKER_PID" "$LOGGER_PID"; do
    [ -n "$child" ] || continue
    kill -TERM "$child" >/dev/null 2>&1 || true
    wait "$child" 2>/dev/null || true
  done
  exit "$status"
}

trap 'cancel_run 130' INT
trap 'cancel_run 143' TERM

for project in "${projects[@]}"; do
  [ -n "$project" ] || continue
  if [ -z "$resume_dir" ] && grep -qxF "$project" "$DOXIS_DIR/state"; then
    echo "== $project: already processed, skipping"
    continue
  fi

  if [ -n "$resume_dir" ]; then
    project_dir="$resume_dir"
  else
    project_dir="$(next_work_dir "$project")"
    mkdir -p "$project_dir"
  fi
  echo "== $(date '+%F %T') pipeline: $project -> $project_dir =="

  if [ -z "$resume_dir" ]; then
    data_file="$DOXIS_DIR/data/$project.yml"
    [ -f "$data_file" ] || data_file="$DOXIS_DIR/data/$project.yaml"
    [ -f "$data_file" ] || data_file="$DOXIS_DIR/data/sample.yml"
    [ -f "$data_file" ] || { echo "  no data file or sample.yml, skipping $project"; continue; }
    cp "$data_file" "$project_dir/input.yml"
  fi

  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker_args=(
    --name "$CONTAINER_NAME"
    --rm
    -e "PROJECT_NAME=$project"
    -e "PUID=$(id -u)"
    -e "PGID=$(id -g)"
  )
  if [ -n "$resume_dir" ]; then
    docker_args+=(-e "RESUME=1")
  fi
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

  ACTIVE_CONTAINER="$CONTAINER_NAME"
  if [ -n "$resume_dir" ]; then
    echo "== $(date '+%F %T') resume run: $project -> $project_dir ==" >> "$project_dir/pipeline.log"
  else
    : > "$project_dir/pipeline.log"
  fi
  exec {log_fd}> >(awk '{ print strftime("%Y-%m-%d %H:%M:%S"), $0; fflush() }' >> "$project_dir/pipeline.log")
  LOGGER_PID=$!
  docker run "${docker_args[@]}" >&"$log_fd" 2>&1 &
  DOCKER_PID=$!
  exec {log_fd}>&-
  unset log_fd
  rc=0
  wait "$DOCKER_PID" || rc=$?
  wait "$LOGGER_PID" || true
  ACTIVE_CONTAINER=""
  DOCKER_PID=""
  LOGGER_PID=""

  echo "  container exit: $rc"
  if [ "$rc" -ne 0 ]; then
    echo "  docker run failed for $project (rc=$rc); log: $project_dir/pipeline.log"
  fi

  if find "$project_dir" -type f -name '*report.md' -print -quit | grep -q .; then
    grep -qxF "$project" "$DOXIS_DIR/state" || echo "$project" >> "$DOXIS_DIR/state"
    echo "== $project: DONE, artifacts in $project_dir"
  else
    echo "== $project: FAILED (no report)"
  fi
done

echo "== finished. state file: $DOXIS_DIR/state (processed: $(grep -c . "$DOXIS_DIR/state"))"
