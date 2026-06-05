[![CI](https://github.com/ebzych/amphimixis/actions/workflows/ci.yml/badge.svg)](https://github.com/ebzych/amphimixis/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-available-blue)](https://github.com/ebzych/amphimixis/tree/main/docs)
[![License](https://img.shields.io/github/license/ebzych/amphimixis?color=8A2BE2)](https://github.com/ebzych/amphimixis/blob/main/LICENSE)

<p align="center">
  <img src="docs/logo.jpg" alt="Amphimixis Logo" width="800"><br>
</p>

# Amphimixis

Amphimixis is an automated project intelligence and evaluation tool for performance and migration readiness. It helps inspect a project for existing infrastructure such as CI, tests, benchmarks, dependencies, and build scripts, then runs builds and collects performance data for further comparison.

Amphimixis simplifies migration readiness exploration and performance analysis by partially implementing our [methodology](docs/migration-readiness-exploring-methodology.md).

> Amphimixis uses `perf` for profiling, makes cross-table with two builds per CPU event for comparison.

<p align="center">
  <img src="docs/tinyxml2-cross-table-example.png" alt="Cross-table example" width="800"><br>
</p>

## Quick run

If you want to try Amphimixis right away, create a virtual environment, install the package from GitHub, and run the full pipeline on a target project:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install git+https://github.com/ebzych/amphimixis.git@stable
amixis init local
amixis run /path/to/project --config local.yml
```

<p align="left">

<img align="right" src="docs/config-example.png" alt="Configuration file example" width="300">

## Note

By default, your working directory must have an `input.yml` or other configuration file that you can specify with the `--config` flag. The format is described in [Config instruction](docs/config_instruction.md).

</p>

If your `input.yml` contains remote machines authenticated with SSH keys, start `ssh-agent` in the current shell and add the required keys manually before running `amixis`:

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_remote_machine
```

## Requirements

- Python 3.12 or later
- Linux
- `rsync` on each machine
- `sshpass` available on the machine where you run Amphimixis, if you connect to remote machines with passwords
- `perf` available on each `run_machine`
- `perf archive`<sup><a href="#note1">1</a></sup> available on each `run_machine`
- A supported build setup in the target project: CMake as the build system and Make as the low-level runner

<p id="note1">

1. More about `perf archive` in [Usage guide](docs/usage_guide.md)

## What Amphimixis does

Amphimixis can:

- <i>analyze</i> a project for CI, tests, benchmarks, build system configuration, and dependencies
- <i>build</i> the project with configured recipes and platforms
- <i>profile</i> executable runs and collect timing and `perf`-based statistics
- <i>compare</i> profiling outputs produced for different builds and put them into a <u><i>cross-table for each CPU event</i></u>

## Typical usage

Prepare a working directory with an `input.yml` configuration file. The configuration format is described in [Config instruction](docs/config_instruction.md).

Run the full workflow for a project:

```bash
amixis run /path/to/project
```

This command:

1. analyzes the project
2. builds it using the selected configuration
3. profiles the resulting executables
4. prints profiling results in the console

To compare two collected `perf` outputs:

```bash
amixis compare build1.scriptout build2.scriptout --max-rows 10
```

`compare` accepts exactly two `.scriptout` files. `--max-rows` limits how many symbols with the largest delta are shown for each event.

For step-by-step command examples, custom configuration files, and `--events` usage, see [Usage guide](docs/usage_guide.md).

## Build and run notes

The tool is distributed as a Python package with the `amixis` CLI entry point.

For local development and reproducible checks, the repository uses `uv` and GitHub Actions. The CI configuration is available in [.github/workflows/ci.yml](.github/workflows/ci.yml).

Useful commands during development:

```bash
uv run amixis --help
uv run pytest
```

If you want a more detailed walkthrough with installation options, workspace preparation, and command examples, see [Usage guide](docs/usage_guide.md).

## Project structure

The repository is organized around a small CLI and several core modules:

- [amixis.py](amixis.py) is the command-line entry point
- [amphimixis/analyzer.py](amphimixis/analyzer.py) inspects a target project
- [amphimixis/builder.py](amphimixis/builder.py) runs configured builds
- [amphimixis/profiler.py](amphimixis/profiler.py) gathers execution and profiling data
- [amphimixis/validator.py](amphimixis/validator.py) validates `input.yml`
- [amphimixis/shell](amphimixis/shell) contains local and remote shell backends
- [docs](docs) contains user-facing documentation

## Documentation

Additional documentation:

- [Usage guide](docs/usage_guide.md)
- [Config instruction](docs/config_instruction.md)
- [Migration readiness exploring methodology](docs/migration-readiness-exploring-methodology.md)

## How To Help

Contributions are welcome.

- Report bugs and suggest improvements through GitHub Issues
- Open a Pull Request with a clear description of the problem and the proposed change
- Add or improve tests for new behavior
- Update documentation when changing CLI behavior or configuration format

Before contributing, make sure local checks pass:

```bash
ci/runner.sh
```

## License

The project is distributed under the license in [LICENSE](LICENSE).

## Third-Party Licenses

This project includes dependencies under various licenses. See [NOTICE.md](NOTICE.md) and the [third_party_licenses/](third_party_licenses/) directory for details.
