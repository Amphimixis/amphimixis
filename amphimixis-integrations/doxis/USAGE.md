# Doxis usage guide

Doxis runs the Amphimixis-AI migration-readiness pipeline in a disposable Docker
container for each project. It analyzes, builds, profiles, and optimizes the
project, then produces a report. Workspaces and results stay on the host after
the container exits.

## Quick start

You need Docker installed with its daemon running and accessible to your user.
Image builds and pipeline runs need network access. Configure access to your
chosen model provider when required; see [Configuration](#configuration).

Create a list containing one project name per line. This example uses a new
list file; choose another filename if it already exists:

```bash
echo "util-linux" > projects
```

Build the image, then run the projects:

```bash
amixis doxis build-image
amixis doxis run projects
```

Or

```bash
amixis doxis run build-image projects
```

The default model is `opencode/big-pickle`. To choose a model and provide an
OpenCode configuration file:

```bash
amixis doxis run doxis-projects.txt \
  --config ./my-opencode.json --model PROVIDER/MODEL
```

Replace `PROVIDER/MODEL` with your provider's model identifier. The image includes
OpenCode, Amphimixis, its agents and tools, build tools, and RISC-V cross-compilation
and QEMU tools. You do not need to install the agents or OpenCode on the host.
The default build configuration compares two local x86 builds; configure
`input.yml` for your intended platforms.

### Find the results

For a first run of a `<project>`, the workspace is
`amphimixis-integrations/doxis/work/<project>_1`. The runner prints the actual path.
It contains `input.yml`, `pipeline.log`, the cloned source, and any generated
reports, `improvements.json`, cross-tables, and profiling artifacts.

Container output is written to `pipeline.log`; the terminal shows workspace
paths, container exit codes, and `DONE` or `FAILED` status. Check those results:
a successful runner exit alone does not establish that every project succeeded.

## Common tasks

### Build and run

`run` uses an existing image and fails if it is missing. To rebuild before running:

Images embed the checkout's code, agents, and tools at build time. Rebuild after
changing them. The default image tag is `amphimixis-opencode:latest`.
For a custom tag, use the same tag for building and running:

```bash
amixis doxis build-image --image my-amphimixis:latest
amixis doxis run doxis-projects.txt --image my-amphimixis:latest
```

Alternatively, set `AMPHIMIXIS_IMAGE`; CLI `--image` takes precedence over it.

### Select projects

Lists contain names, rather than repository URLs. Blank lines are ignored;
only the first whitespace-separated field of each nonblank line is used.
Do not add comment lines: they are treated as project names.

```bash
amixis doxis run projects --skip 2 --limit 3
```

This selects up to three entries after the first two. Both values must be
non-negative integers; `--limit 0` selects none.

### Specify a repository or add instructions

By default, the agent searches GitHub/GitLab for the project's repository.
Use a one-project list when specifying a repository, because the same URL is
passed to every selected project's container:

```bash
amixis doxis run projects --limit 1 \
  --repo https://github.com/leethomason/tinyxml2.git
```

`--prompt` adds instructions to the generated pipeline prompt:

```bash
amixis doxis run projects --limit 1 \
  --prompt 'Focus the report on portability and explain any profiling limitations.'
```

### Choose where workspaces are saved

```bash
amixis doxis run projects --workdir ./doxis-workspaces
```

`--workdir` sets the parent directory for all selected projects. Each fresh run
creates `<project>_<i>` using the first available positive suffix: `_1`, then
`_2`, and so on, reusing a gap if an earlier workspace was deleted. Existing
workspaces are preserved and never automatically cleaned up.

The processed-project `state` file stays in `amphimixis-integrations/doxis`,
even with a custom workspace parent.

## Configuration

Doxis uses two different configuration files:

| Configuration | Purpose | How to supply it |
| --- | --- | --- |
| OpenCode JSON | Model providers and OpenCode settings | `--config ./my-opencode.json` |
| Amphimixis YAML | Build platforms, recipes, and executables | Per-project file under `amphimixis-integrations/doxis/data/` |

`--config` must point to an existing host file. It is mounted read-only at
`/etc/opencode/opencode.json` and selected using `OPENCODE_CONFIG` inside the
container. Host OpenCode settings and credentials are not automatically mounted;
make the provider settings and credentials needed for your run available inside
the container.

For fresh runs, Doxis copies the first existing file below into the workspace
as `input.yml`:

1. `amphimixis-integrations/doxis/data/<project>.yml`
2. `amphimixis-integrations/doxis/data/<project>.yaml`
3. `amphimixis-integrations/doxis/data/sample.yml`

See the [Amphimixis configuration reference](../../docs/config_instruction.md)
for YAML fields and the [Amphimixis-AI guide](../../docs/amphimixis-ai.md) for
pipeline details.

## Resume or start again

### Resume an interrupted workspace

Resume keeps the same workspace and `input.yml`, appends output to `pipeline.log`,
and instructs the agent to read the log, inspect existing results, and continue
unfinished work:

```bash
amixis doxis run --resume amphimixis-integrations/doxis/work/<project>_1
```

The workspace must contain both `input.yml` and `pipeline.log`. Doxis recovers
the project name and model, unless
`--model` is supplied. Re-supply any needed `--config`, image selection, Docker
arguments, or additional prompt. Missing files or startup metadata cause an error
before a container starts or the log changes. With an explicit rebuild, image
building happens before this workspace validation.

Do not combine `--resume` with a list file, `--skip`, `--limit`, or `--workdir`.

### Start a fresh attempt

Fresh runs skip names recorded in `amphimixis-integrations/doxis/state`.
To rerun one, remove only its exact line from that file in a text editor, then
run the project list again. Doxis creates a new numbered workspace and copies
its starting configuration from `data/` again.

A project is recorded as processed when the runner finds **any file matching
`*report.md` anywhere in its workspace**, even if the container exited with an
error. `DONE` means that a report exists; inspect the report and log to assess
whether the pipeline completed successfully. Without a report, the runner
prints `FAILED` and does not add a new state entry. An existing state entry is
not removed by a failed resume.

## Command reference

Bare `amixis doxis` prints usage. Use `amixis doxis run --help` or
`amixis doxis build-image --help` for command help.

| CLI command | Behavior |
| --- | --- |
| `amixis doxis build-image [--image TAG]` | Build only; accepts `--image` and help |
| `amixis doxis run <list-file> [options]` | Run using an existing image |
| `amixis doxis run build-image <list-file> [options]` | Build, then run |
| `amixis doxis run --resume PATH [options]` | Continue an existing workspace |

Options for `amixis doxis run`:

| Option | Meaning |
| --- | --- |
| `--limit N` | Select at most N list entries after `--skip` |
| `--skip M` | Skip the first M list entries; default `0` |
| `--repo URL` | Supply the same repository URL to every selected project on fresh runs |
| `--config PATH` | Mount an existing OpenCode JSON configuration read-only |
| `--model PROVIDER/MODEL` | Default `opencode/big-pickle`; resume restores the logged model |
| `--prompt TEXT` | Append instructions to the generated prompt |
| `--workdir PATH` | Parent for new numbered workspaces; default `amphimixis-integrations/doxis/work` |
| `--resume PATH` | Resume a workspace; excludes list and selection/workdir options |
| `--extra-docker ARG` | Pass one argument to `docker run`; repeat for each argument |
| `--image TAG` | Override `AMPHIMIXIS_IMAGE` and the default image tag |
| `-h`, `--help` | Show command help |

For the CLI, values starting with `-` need the equals form. Each Docker option
and its value are separate arguments; do not combine them into one string:

```bash
amixis doxis run projects \
  --extra-docker=--cap-add --extra-docker PERFMON
```

### Shell-script equivalents

The scripts require Bash and Docker, without a host `amixis` installation.
`build-and-run.sh` builds by default, then runs the pipeline through
`process-projects.sh`:

```bash
# Build and run.
bash amphimixis-integrations/doxis/build-and-run.sh projects

# Build only; no list file needed.
bash amphimixis-integrations/doxis/build-and-run.sh --no-run

# Run with an existing image.
bash amphimixis-integrations/doxis/build-and-run.sh projects --no-build

# Resume with an existing image.
bash amphimixis-integrations/doxis/build-and-run.sh \
  --resume amphimixis-integrations/doxis/work/<project>_1 --no-build
```

| Script option | Meaning |
| --- | --- |
| `--no-build` | Use an existing image; error if it is missing |
| `--no-run` | Skip the pipeline; build only unless `--no-build` is also supplied |
| Runtime options | Same options as CLI `run`, except `--image`; use space-separated option/value pairs |

Set `AMPHIMIXIS_IMAGE` to select a script's image; scripts do not accept
`--image`. Unlike the CLI, scripts require the space-separated form for
`--extra-docker`, including values starting with `-`:

```bash
AMPHIMIXIS_IMAGE=my-amphimixis:latest \
  bash amphimixis-integrations/doxis/build-and-run.sh projects \
  --no-build --extra-docker --cap-add --extra-docker PERFMON
```

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Docker unavailable or access denied | Start the Docker daemon and verify `docker info` works for your user |
| Image not found | Run `amixis doxis build-image`; use the same tag when building and running |
| CLI cannot locate Doxis scripts | Run from a repository checkout; a wheel alone does not include the harness scripts |
| OpenCode config missing or provider authentication fails | Check the host `--config` path and provide the required settings/credentials inside the container |
| No project input configuration | Restore `data/sample.yml` or add `data/<project>.yml` or `.yaml`; paths here are under `amphimixis-integrations/doxis/` |
| Project unexpectedly skipped | Check the shared `state` file and remember that selection happens before state filtering |
| `FAILED (no report)` or a nonzero container exit | Read the workspace's `pipeline.log`; fix the cause, then resume or start fresh |
| Resume rejected | Check for `input.yml`, `pipeline.log`, and a valid entrypoint project/model startup line; omit selection flags |
| Profiling permission errors | Check host perf restrictions and Docker capabilities; add required capabilities with `--extra-docker` for your environment |

The entrypoint attempts to set `perf_event_paranoid=-1`, but continues if that
setting is not writable. A running container alone does not guarantee that
profiling permissions are available.
