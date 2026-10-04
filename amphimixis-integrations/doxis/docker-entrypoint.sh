#!/usr/bin/env bash
# Environment:
#   PROJECT_NAME   source-package / project name (required)
#   PROJECT_REPO   optional explicit GitHub URL (overrides the agent's search)
#   PIPELINE_PROMPT additional prompt to the agent
#   MODEL          opencode model in the form provider/model (default: opencode/big-pickle)
#   OPENCODE_CONFIG  path to an optional opencode config file (opencode env var)
set -euo pipefail

: "${PROJECT_NAME:?PROJECT_NAME environment variable is required}"
MODEL="${MODEL:-opencode/big-pickle}"

if [ -n "${PIPELINE_PROMPT:-}" ]; then
  ADDITIONAL_PROMPT="${PIPELINE_PROMPT}"
else
  ADDITIONAL_PROMPT=""
fi

if [ -n "${PROJECT_REPO:-}" ]; then
  REPO_INSTRUCTION="The project repository URL is ${PROJECT_REPO}. Clone exactly this URL into the workspace. Do not search for a different repository."
else
  REPO_INSTRUCTION="Search GitHub/GitLab for the active repository of the source package \"${PROJECT_NAME}\" (prefer the repo with the latest commits and tags, the most stars and an active upstream). Take the resolved clone URL and record it in the report. If no clearly matching repository exists, document that and finish the report marking the data as NOT AVAILABLE."
fi

PROMPT="$(cat <<EOF
You are applying the Amphimixis migration readiness pipeline to the single project "${PROJECT_NAME}" inside this disposable container.

CONTEXT:
- Reference platform: x86_64 (the local container machine). Target platform can be either x86_64 or riscv (if target platform is different from build platform and does not contain address -- use cross-compilation tools and qemu-user emulation).
- The Amphimixis config file input.yml is ALREADY provided in the current working directory (/work).
- ${REPO_INSTRUCTION}
- Working workspace: /work/${PROJECT_NAME}-workspace.

RULES:
- NEVER fabricate profiling data. Mark anything unmeasured as NOT AVAILABLE; label reconstructed data as RECONSTRUCTED (not measured).
- improvements.json, cross-tables/CT-*.md and the saved profile JSON/YAML/pkl are tool-owned and read-only for you.
- Do not read pipeline.log file.
- When every phase is finished and the report is saved, print exactly the line: WORK ON THE ${PROJECT_NAME} IS COMPLETED

ADDITIONAL INSTRUCTIONS:
- ${ADDITIONAL_PROMPT}
EOF
)"

cd /work

echo -1 > /proc/sys/kernel/perf_event_paranoid 2>/dev/null && echo "[entrypoint] perf_event_paranoid=-1" || echo "[entrypoint] perf_event_paranoid not writable (ok)"

echo "[entrypoint] opencode: starting pipeline for ${PROJECT_NAME} (model=${MODEL})"
set +e
opencode run --format json --auto --agent amphimixis -m "${MODEL}" -- "${PROMPT}"
rc=$?
set -e

puid="${PUID:-1000}"
pgid="${PGID:-1000}"
chown -R "${puid}:${pgid}" /work 2>/dev/null || true

echo "[entrypoint] opencode finished for ${PROJECT_NAME} (rc=${rc})"
exit "${rc}"
