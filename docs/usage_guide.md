# Usage Guide

> If you encounter issues while using Amphimixis, see [Troubleshooting](troubleshooting.md) for common problems and solutions.

## Requirements

- Python 3.12 or later
- Linux
- `rsync` on each machine
- `sshpass` on the machine that connects to remote hosts with passwords
- `perf` and `perf archive` on each `run_machine`
- Target project must support CMake as the build system and Make or Ninja as the low-level runner

See [Troubleshooting → System Dependencies](troubleshooting.md#system-dependencies) for installation commands and the `perf archive` setup.

## Quick Start

If you want to try Amphimixis right away, create a virtual environment, install
the package from GitHub, and run the full pipeline on a target project:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install git+https://github.com/Amphimixis/amphimixis
amixis init local
amixis run /path/to/project --config local.yml
```

## Choose an installation method

- **For the LLM-agent workflow — install with Opencode integration:**

The `amixis opencode` command runs Amphimixis inside [Opencode](https://opencode.ai) as an
LLM-powered orchestrator agent:

```bash
git clone https://github.com/Amphimixis/amphimixis
cd amphimixis
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Then, from your target project folder, install the methodology agents and tools — `amixis opencode install` copies them into the project's `.opencode` directory:

```bash
cd path/to/your/project
amixis opencode install
```

- **For users — install `amixis` with pip** — the venv + `pip install` setup is the same as in [Quick Start](#quick-start), then continue below.

This is the recommended path if you only want to run `amixis` and do not want to install anything into the system Python environment.

- **For development — clone and install with uv:**

```bash
git clone https://github.com/Amphimixis/amphimixis
cd amphimixis
uv sync
```

- **To test the packaged artifact — build a local wheel:**

```bash
python3 -m venv .venv
source .venv/bin/activate
uv build
pip install dist/*.whl
```

## Prepare a workspace

Run Amphimixis from a working directory that contains your configuration and any generated artifacts. Before starting, create an `input.yml` file there.

### Create a configuration file

- Start using provided config file sample:

  ```bash
  amixis init sample-name
  ```

  Available sample name:
  - local
  - distributed
  - distributed-cross

- Or create config with template:

  ```bash
  amixis add input
  ```

- Configuration reference: [Configuration File Guide](config_instruction.md)
- Example file: [Example Configuration File](input.yml)

### Understand the expected configuration

At minimum, `input.yml` should describe:

- the build system and runner
- the target platforms
- the build recipes
- the builds that connect platforms and recipes

In `builds`, you can optionally specify an `executables` list for each build. Each path must be relative to that build's output directory, for example, `bin/my_app`. If `executables` is omitted, Amphimixis profiles the first executable file it finds in the build directory.

### Using SSH keys

You can use Amphimixis with SSH keys. See [Troubleshooting → sshpass **not found**](troubleshooting.md#sshpass-not-found) for setup.

## Run the main workflow

```bash
amixis run /path/to/project
```

Use `--config` to specify a custom configuration file path:

```bash
amixis run --config ./my_input.yml /path/to/project
```

The full pipeline:

1. analyzes the project
1. builds it using the selected configuration
1. profiles the resulting executables
1. prints profiling results in the console

A human-readable `perf stat` output is saved as `<project name>.json`. To save it as YAML instead, use `--stats-format` (works with both `run` and `profile`):

```bash
amixis run /path/to/project --stats-format yaml
```

## Run individual commands

Analyze only:

```bash
amixis analyze /path/to/project
```

Build only:

```bash
amixis build /path/to/project
```

To build a **specific** build from the configuration file, use `--build-name`:

```bash
amixis build /path/to/project --build-name 1_2_1
```

The `--build-name` value must match one of the build entries in your `input.yml` (format: `<build_machine>_<run_machine>_<recipe_id>`). If omitted, every build in the configuration is processed.

Profile only:

```bash
amixis profile /path/to/project
```

To profile a **specific** build, use `--build-name`:

```bash
amixis profile /path/to/project --build-name 1_2_1
```

If omitted, profiling runs on every successful build that matches the configuration.

`run` and `profile` commands saves a human-readable perf stat file `\<project name\>.json`. Use `--stats-format yaml` to get YAML instead of JSON:

```bash
amixis profile /path/to/project --stats-format yaml
```

Validate a configuration file:

```bash
amixis validate /path/to/input/config
```

## Work with perf events

The same flag works with profiling-only mode:

```bash
amixis profile /path/to/project --events cycles cache-misses
```

With the main pipeline or `profile`, `--events` tells `perf record` which events to collect.

## Compare profiling outputs

To compare two collected `.scriptout` files:

```bash
amixis compare build1.scriptout build2.scriptout
```

To limit how many symbols with the largest delta are shown for each event:

```bash
amixis compare build1.scriptout build2.scriptout --max-rows 10
```

Every comparison also saves the cross-tables as Markdown to `cross-tables/CT-<first file>-<second file>.md`, independently of how they are printed. To print the cross-tables themselves as Markdown tables instead of the default plain-text format, use `--cross-table-format` (`md` is an alias of `markdown`):

```bash
amixis compare build1.scriptout build2.scriptout --cross-table-format markdown
```

## Add a toolchain

Add a new toolchain to the global configuration file:

```bash
amixis add toolchain
```

## Clean build directories

If you want to clean up your build directories from previous builds, use:

```bash
# To interactively select builds to clean
amixis clean

# To clean specific builds by name
amixis clean build-name-1 build-name-2 ...

# To clean all builds
amixis clean --all
```
