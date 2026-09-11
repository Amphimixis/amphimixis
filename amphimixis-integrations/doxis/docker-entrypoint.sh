#!/usr/bin/env bash
# amphimixis-entrypoint.sh — run the Amphimixis opencode agent for ONE project.
#
# Environment:
#   PROJECT_NAME   source-package / project name (required)
#   PROJECT_REPO   optional explicit GitHub URL (overrides the agent's search)
#   PIPELINE_PROMPT plain-text pipeline prompt that overrides the
#                  generated one (optional)
#   MODEL          opencode model in the form provider/model (default: opencode/big-pickle)
#   OPENCODE_CONFIG  path to an optional opencode config file (opencode env var)
set -euo pipefail

: "${PROJECT_NAME:?PROJECT_NAME environment variable is required}"
MODEL="${MODEL:-opencode/big-pickle}"

if [ -n "${PIPELINE_PROMPT:-}" ]; then
  PROMPT="${PIPELINE_PROMPT}"
else
  if [ -n "${PROJECT_REPO:-}" ]; then
    REPO_INSTRUCTION="The project repository URL is ${PROJECT_REPO}. Clone exactly this URL into the workspace. Do not search for a different repository."
  else
    REPO_INSTRUCTION="Search GitHub/GitLab for the active repository of the source package \"${PROJECT_NAME}\" (prefer the repo with the latest commits and tags, the most stars and an active upstream). Take the resolved clone URL and record it in the report. If no clearly matching repository exists, document that and finish the report marking the data as NOT AVAILABLE."
  fi

  PROMPT="$(cat <<EOF
You are applying the Amphimixis migration readiness pipeline to the single project "${PROJECT_NAME}" inside this disposable container.

CONTEXT:
- Reference platform: x86_64 (the local container machine). There is no second platform — target architecture is the same x86_64.
- The Amphimixis config file input.yml is ALREADY provided in the current working directory (/work). It defines two local builds: 1_1_1 (baseline) and 1_1_2 (optimized with -O3). Use amphimixis-validate to confirm your configurator keeps it correct; fix only invalid fields, do not recreate it from scratch.
- ${REPO_INSTRUCTION}
- Working workspace: /work/${PROJECT_NAME}-workspace — the analyzer clones the repository into it; the builder and profiler operate on it.
- Current working directory is /work.

RUN THE FULL PIPELINE:
1. amphimixis-analyzer: resolve and clone the repository, analyze structure, tests, CI, build systems, platform-specific macros and dependencies.
2. amphimixis-configurator: validate /work/input.yml (fix only invalid fields).
3. amphimixis-builder: build both builds 1_1_1 and 1_1_2 locally in the workspace and run tests if present. If a build fails due to a missing dependency, install it with apt-get/ninja/etc. (this container is disposable, restrictions are relaxed here) and retry.
4. amphimixis-profiler: profile the executables of 1_1_1 and 1_1_2 with full experimental rigor (warmup, 6-10 runs, taskset pinning, nice, frequency check); create a cross-table comparing the two builds with \`amixis compare --cross-table-format markdown\`; analyze vectorization.
5. amphimixis-optimizer: deep causal analysis of the bottlenecks and recommendations.
6. Final report: compile the standard 7-section Amphimixis report. Save it as /work/amphimixis-${PROJECT_NAME}-report.md (the formal Amphimixis report inspector only recognizes the amphimixis- prefixed name). Use the calculate-optimization-improvement tool for every changed metric and embed the results as the standard Improvement section, and embed the cross-table section exactly from cross-tables/CT-*.md.

RULES:
- NEVER fabricate profiling data. Mark anything unmeasured as NOT AVAILABLE; label reconstructed data as RECONSTRUCTED (not measured).
- improvements.json, cross-tables/CT-*.md and the saved profile JSON/YAML/pkl are tool-owned and read-only for you.
- No raw perf stat dumps in the report; use the structured data only.
- When every phase is finished and the report is saved, print exactly the line: WORK ON THE ${PROJECT_NAME} IS COMPLETED
EOF
)"
fi

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
