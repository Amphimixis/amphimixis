# Dockerized Amphimixis Pipeline — Usage

The doxis harness runs the Amphimixis-AI migration-readiness pipeline inside a
disposable Docker container per project. The pipeline is driven by a single
entrypoint script: `build-and-run.sh`.

Before you start, please:

1. Read [`docs/amphimixis-ai.md`](../../docs/amphimixis-ai.md) to understand the
   Amphimixis-AI agent system, the pipeline, and its installation.
2. Make sure `docker` is installed.

The Amphimixis agents and tools are installed into the image at build time via
`amixis opencode install --global` (the image is built from the repository
root, so it always embeds the current agents/tools). Nothing has to be
generated or installed on the host.

## Current constraints

- Fresh runs process a **list of project names** (not arbitrary URLs). The
  list file should contain one project name per line.
- The LLM **model defaults to `opencode/big-pickle`**; override it with
  `--model PROVIDER/MODEL`.
- A custom **opencode config** can be mounted read-only with `--config PATH`
  (useful to configure providers and authentication). It is loaded inside the
  container via the `OPENCODE_CONFIG` environment variable.
- Each container uses its **`input.yml` from `doxis/data/<project>.yml`**
  (or `.yaml`) **if specified for that project, otherwise
  `doxis/data/sample.yml`** is used as the input.
- Every fresh run gets a never-cleaned numbered work directory
  `doxis/work/<project>_<i>`, where `<i>` is the ordinal equal to the number of existing work directories for that project plus one.
  The first run
  creates `doxis/work/<project>_1`. All artifacts (report, `improvements.json`,
  cross-tables, profile data, `pipeline.log`) remain in this directory.
- Projects already recorded in `doxis/state` are skipped, so a project runs
  only once. To run it again, remove it from `state`; the next run then creates
  the next numbered work directory.

---

## Usage

`build-and-run.sh` rebuilds the Docker image (unless `--no-build`) and then
runs the pipeline over the project list:

```bash
amphimixis-integrations/doxis/build-and-run.sh <list-file> [options]
```

It performs two steps:

1. Builds the Docker image `amphimixis-opencode:latest` from the repository
   root. `--no-build` skips this step and uses an existing image.
2. Forwards the remaining arguments to the internal `./process-projects.sh` and
   starts it (one disposable container per project).

Example:

```bash
./build-and-run.sh projects --limit 1 --config my-opencode.json --model opencode/big-pickle
```

### Via the `amixis` CLI

From a repository checkout, the same pipeline is available as
`amixis doxis` subcommands:

```bash
amixis doxis build-image
amixis doxis run projects --limit 1 --config my-opencode.json --model opencode/big-pickle
amixis doxis run build-image projects --skip 2
AMPHIMIXIS_IMAGE=my-tag amixis doxis run projects
```

- Bare `amixis doxis` prints usage.
- `amixis doxis build-image [--image TAG]` builds the image only.
- `amixis doxis run <list-file> [flags]` runs the pipeline and never
  builds (fails if the image is missing — build it first).
- `amixis doxis run build-image <list-file> [flags]` builds the image
  and then runs the pipeline.
- `amixis doxis run --resume PATH [flags]` resumes directly from a workspace.
- `run` accepts `--limit/--skip/--repo/--config/--model/--prompt/--workdir/--resume/` `--extra-docker/--image`;
  `build-image` accepts only `--image`.

Notes:

- `amixis doxis` forwards to `process-projects.sh` / `build-and-run.sh`, so
  `docker` and a repo checkout are still required (it is not available
  from a pip-installed wheel without the checkout).
- `--image TAG` overrides `$AMPHIMIXIS_IMAGE` for this run.
- Values starting with `-` need the `=` form:
  `--extra-docker=--privileged`.

Arguments:

| Argument | Meaning |
|---|---|
| `<list-file>` | File listing project names, one per line (required for fresh runs only) |
| `--limit N` | Process only the first N projects |
| `--skip M` | Skip first M projects |
| `--repo URL` | Explicit project repository URL, passed to the container as `PROJECT_REPO` (overrides the agent's search, one for all containers) |
| `--config PATH` | Custom opencode config (JSON), mounted read-only and loaded via `OPENCODE_CONFIG` |
| `--model PROVIDER/MODEL` | LLM model for opencode (default: `opencode/big-pickle`; resume restores the logged model unless overridden) |
| `--no-build` | Skip the image build step and run against the existing image |
| `--workdir PATH` | Parent for new numbered `<project>_<i>` workspaces, regardless of the number of selected projects (default: `doxis/work`) |
| `--resume PATH` | Recover the project and model from an existing workspace without a list file; preserve `input.yml`, append to `pipeline.log`, and instruct OpenCode to read the log before continuing |
| `--extra-docker ARG` | Extra argument(s) passed through to `docker run` (repeatable) |
| `-h` / `--help` | Print usage |

The image tag defaults to `amphimixis-opencode:latest` and can be overridden
with the `AMPHIMIXIS_IMAGE` environment variable.

### Resuming interrupted work

```bash
./build-and-run.sh --resume doxis/work/util-linux_1 --no-build
amixis doxis run --resume doxis/work/util-linux_1
```

Resume requires an existing `input.yml` and `pipeline.log`, and bypasses the
completed-project state check. It recovers the project and model from the latest
matching `[entrypoint] opencode: starting pipeline for <project> (model=<model>)`
entry anywhere in the log, including timestamped entries. Missing or malformed
startup metadata produces an error before the container starts or the log is
changed. Validation runs in `process-projects.sh`, after any requested image build.
Use `--model` to override the recovered model.

A list file, `--limit`, `--skip`, and `--workdir` cannot be combined with
`--resume`. Other runtime flags remain optional. OpenCode reads the log to
recover project context and completed actions, checks existing artifacts, and
continues unfinished work.

To start fresh under a custom parent directory:

```bash
amixis doxis run projects --workdir /path/to/workspaces
```

### Directory layout

| Path | Purpose |
|---|---|
| `doxis/projects` | Project list (one name per line) |
| `doxis/data/<project>.yml` | Per-project `input.yml` configs. A project's container input file comes from `data/<project>.yml` (or `.yaml`) when it exists; otherwise the container uses `data/sample.yml` as the input |
| `doxis/work/<project>_<i>` | Numbered container workspace (bind-mounted as `/work`); holds all artifacts |
| `doxis/state` | Projects already processed, one per line |
