# Contributing Guide

Thank you for contributing to Amphimixis. This guide is based on the current repository layout and CI scripts, so you can use it as a practical checklist when preparing changes.

## Project Snapshot

Amphimixis is a Python CLI tool for analyzing projects, running builds, profiling executables, and comparing collected performance data.

The repository is organized around a few main areas:

- `amphimixis/` contains the application modules and assets
   - `core` contains core application modules
   - `samples` contains example configuration files
   - `amixis` is console utility module of Amphimixis
      - `__main__.py` is the CLI entry point
- `tests/` contains unit and integration tests
- `docs/` contains user-facing documentation
- `ci/` contains local scripts that mirror the GitHub Actions checks

## Development Environment

Current project requirements:

- Python `3.12+`
- Linux
- `uv`
- `mdl` for Markdown linting
- `shellcheck` for validating CI shell scripts

To set up the project locally:

```bash
git clone https://github.com/Amphimixis/amphimixis.git
cd amphimixis
uv sync
```

If you want to use the repository's helper scripts, make sure `mdl` and `shellcheck` are installed first. The `ci/environment_configure.sh` script will also try to install `uv` if it is missing.

## Before You Open An Issue

For bug reports, please include:

- a concise title
- what you expected to happen
- what actually happened
- a minimal reproduction scenario
- your environment details:
   - Python version
   - Linux distribution
   - relevant build tools
   - whether the run was local or remote
- `amphimixis.log` file (check sensitive data before)

For feature requests or larger refactorings, opening an issue first is strongly preferred. It helps align on scope before implementation starts.

## Development Workflow

Recommended workflow:

1. Create a branch from `main`.
1. Keep the change focused on one problem.
1. Add or update tests when behavior changes.
1. Update documentation when CLI behavior, configuration, or examples change.
1. Run the relevant checks locally before opening a pull request.

## Local Checks

The repository already contains scripts that mirror CI. The simplest way to run the full validation flow is:

```bash
./ci/runner.sh
```

This runs:

- Markdown linting with `mdl`
- formatting check with `black --check`
- linting with `ruff`
- type checking with `mypy`
- linting with `pylint`
- unit tests
- integration tests

If you want to run the tools manually, these commands match the current scripts:

```bash
uv run black --check $(git ls-files ':/*.py')
uv run ruff check $(git ls-files ':/*.py')
uv run mypy $(git ls-files ':/*.py')
uv run pylint $(git ls-files ':/*.py')
PYTHONPATH=$(git rev-parse --show-toplevel) uv run pytest $(git rev-parse --show-toplevel) -m unit
PYTHONPATH=$(git rev-parse --show-toplevel) uv run pytest $(git rev-parse --show-toplevel) -m integration
mdl -r '~MD013','~MD033' $(git ls-files ':/*.md')
```

Integration tests may require Docker-related tooling depending on the scenario under test.

## Tests

The repository uses two main test categories:

- `unit` for isolated behavior
- `integration` for end-to-end and environment-sensitive scenarios

Please add a regression test when fixing a bug if it is practical to do so.

## Documentation

When user-facing behavior changes, update the relevant docs in the same pull request:

- `README.md`
- `docs/usage_guide.md`
- `docs/config_instruction.md`
- `samples/*.yml` if example configuration should change

## Pull Requests

A good pull request usually:

- explains what changed and why
- references related issues when applicable
- includes tests for the new or changed behavior
- keeps documentation in sync
- passes local checks and CI

Smaller pull requests are easier to review and merge quickly.

## Commit Messages

Readable history is appreciated. Short, descriptive commit messages are preferred, especially when they make it obvious whether the change is a fix, refactor, test update, or documentation update.

## Contributors

Current project authors are listed in `pyproject.toml`.

Additional contributors:

- Kirill Smirnov
