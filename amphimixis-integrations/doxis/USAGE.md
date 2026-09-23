# Dockerized Amphimixis Pipeline — Usage

The doxis harness runs the Amphimixis-AI migration-readiness pipeline inside a
disposable Docker container per project. The pipeline is driven by a single
entrypoint script: `rebuild-and-run.sh`.

Before you start, please:

1. Read [`docs/amphimixis-ai.md`](../../docs/amphimixis-ai.md) to understand the
   Amphimixis-AI agent system, the pipeline, and its installation.
2. Make sure `docker` is installed.

The Amphimixis agents and tools are installed into the image at build time via
`amixis opencode install --global` (the image is built from the repository
root, so it always embeds the current agents/tools). Nothing has to be
generated or installed on the host.

## Current constraints

- The pipeline processes a **list of project names** (not arbitrary URLs). The
  list file should contain one project name per line (`#` comments are
  allowed, the first whitespace-separated token of each line is used).
- The LLM **model defaults to `opencode/big-pickle`**; override it with
  `--model PROVIDER/MODEL`.
- A custom **opencode config** can be mounted read-only with `--config PATH`
  (useful to configure providers and authentication). It is loaded inside the
  container via the `OPENCODE_CONFIG` environment variable.
- Each container uses its **`input.yml` from `doxis/data/<project>.yml`**
  (or `.yaml`) **if specified for that project, otherwise
  `doxis/data/sample.yml`** is used as the input.
- Every run gets a fresh, never-cleaned numbered work directory
  `doxis/work/<project>_<i>`, where `<i>` is the ordinal equal to "number of
  already existing work directories for that project + 1". The first run
  creates `doxis/work/<project>_1`. All artifacts (report, `improvements.json`,
  cross-tables, profile data, `pipeline.log`) remain in this directory.
- Projects already recorded in `doxis/state` are skipped, so a project runs
  only once. To run it again, remove it from `state`; the next run then creates
  the next numbered work directory.

---

## Usage

`rebuild-and-run.sh` rebuilds the Docker image (unless `--no-build`) and then
runs the pipeline over the project list:

```bash
amphimixis-integrations/doxis/rebuild-and-run.sh <list-file> [options]
```

It performs two steps:

1. Builds the Docker image `amphimixis-opencode:latest` from the repository
   root. `--no-build` skips this step and uses an existing image.
2. Forwards the remaining arguments to the internal `pipeline/run.sh` and
   starts it (one disposable container per project).

Example:

```bash
./rebuild-and-run.sh projects --limit 1 --config my-opencode.json --model opencode/big-pickle
```

Arguments:

| Argument | Meaning |
|---|---|
| `<list-file>` | File listing project names, one per line (should come first) |
| `--limit N` | Process only the first N projects |
| `--from M` | Start from project index M (0-based) |
| `--repo URL` | Explicit project repository URL, passed to the container as `PROJECT_REPO` (overrides the agent's search, one for all containers) |
| `--config PATH` | Custom opencode config (JSON), mounted read-only and loaded via `OPENCODE_CONFIG` |
| `--model PROVIDER/MODEL` | LLM model for opencode (default: `opencode/big-pickle`) |
| `--no-build` | Skip the image build step and run against the existing image |
| `--extra-docker ARG` | Extra argument(s) passed through to `docker run` (repeatable) |
| `-h` / `--help` | Print usage |

The image tag defaults to `amphimixis-opencode:latest` and can be overridden
with the `AMPHIMIXIS_IMAGE` environment variable.

### Directory layout

| Path | Purpose |
|---|---|
| `doxis/projects` | Project list (one name per line) |
| `doxis/data/<project>.yml` | Per-project `input.yml` configs. A project's container input file comes from `data/<project>.yml` (or `.yaml`) when it exists; otherwise the container uses `data/sample.yml` as the input |
| `doxis/work/<project>_<i>` | Numbered container workspace (bind-mounted as `/work`); never cleaned, holds all artifacts |
| `doxis/state` | Projects already processed, one per line |
