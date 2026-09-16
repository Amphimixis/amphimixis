# Dockerized Amphimixis Pipeline — Usage

The doxis harness runs the Amphimixis-AI migration-readiness pipeline inside a
disposable Docker container per project. This document describes the two ways
to use it.

Before you start, please:

1. Read [`docs/amphimixis-ai.md`] to understand the
   Amphimixis-AI agent system, the pipeline, and its installation.
2. Install Amphimixis-AI locally in the `amphimixis` repository, so the agent
   sources in `.opencode/agents/` are present. They are the input for the
   "softened" agents used inside the image. If agents are missing or outdated,
   regenerate them first with the `agents-regenerator` agent.

## Current constraints

- The pipeline processes a **list of project names** (not arbitrary URLs). The
  list file should contain one project name per line (`#`
  comments are allowed, the first whitespace-separated token of each line is
  used).
- The LLM **model inside the container is hard-coded to `big-pickle`**.
- Each container uses its **`input.yml` from `doxis/data/<project>.yml`**
  (or `.yaml`) **if specified for that project, otherwise `doxis/data/sample.yml`**
  is used as the input.
- Artifact flow: the container writes everything into the bind-mounted work
  directory `doxis/work/<project>/`; when the container finishes, the
  artifacts are copied to `doxis/results/<project>/` and the work directory is
  cleared.

---

## Way 1 — automated: `rebuild-and-run.sh`

One script that recreates the softened agents, rebuilds the Docker image, and
then runs the pipeline:

```bash
amphimixis-integrations/doxis/rebuild-and-run.sh
<list-file> [--limit N] [--from M] [--repo URL] [--extra-docker ARG]
```

It performs three steps automatically:

1. Regenerates the softened agents from the local `.opencode/agents/` sources
   by running `pipeline/soften_agents.py`.
2. Rebuilds the Docker image (`amphimixis-opencode:latest`).
3. Forwards the remaining arguments to `pipeline/run.sh` and starts it.

Example:

```bash
./rebuild-and-run.sh projects --limit 1
```

Arguments:

| Argument | Meaning |
|---|---|
| `<list-file>` | File listing project names, one per line (should come first)|
| `--limit N` | Process only the first N projects |
| `--from M` | Start from project index M (0-based) |
| `--repo URL` | Explicit project repository URL, passed to the container as `PROJECT_REPO` (overrides the agent's search, one for all containers) |
| `--extra-docker ARG` | Extra argument(s) passed through to `docker run` (repeatable) |
| `-h` / `--help` | Print usage |

## Way 2 — manual

The same steps, executed by hand:

1. Regenerate the softened agents for the container:

   ```bash
   python3 amphimixis-integrations/doxis/pipeline/soften_agents.py
   ```

   This copies each `amphimixis*.md` agent from `.opencode/agents/` into
   `amphimixis-integrations/doxis/agents-docker/` and scales the bash
   permission to `"*": allow` so the disposable container can run `perf`,
   `apt-get`, etc.

2. Build the Amphimixis Docker image (from the repository root):

   ```bash
   docker build -f amphimixis-integrations/doxis/Dockerfile -t amphimixis-opencode:latest .
   ```

3. Start the pipeline over a project list:

   ```bash
   amphimixis-integrations/doxis/pipeline/run.sh <list-file> [--limit N] [--from M] [--extra-docker ARG]
   ```

   Example:

   ```bash
   ./pipeline/run.sh projects --limit 1
   ```

### Directory layout

| Path | Purpose |
|---|---|
| `doxis/projects` | Project list (one name per line) |
| `doxis/data/<project>.yml` | Per-project `input.yml` configs. A project's container input file comes from `data/<project>.yml` (or `.yaml`) when it exists; otherwise the container uses `data/sample.yml` as the input |
| `doxis/work/<project>/` | Live container workspace (bind-mounted as `/work`), cleared after the run |
| `doxis/results/<project>/` | Curated artifacts (report, `improvements.json`, cross-tables, profile data, log) |
| `doxis/state` | Projects already processed, one per line |
| `doxis/agents-docker/` | Softened agent definitions baked into the image |
