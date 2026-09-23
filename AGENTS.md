# AGENTS.md for Amphimixis project

## Read to understand the main purpose of the project and tool usage

1. `README.md`
2. `docs/usage_guide.md`
3. `docs/config_instructions.md`
4. `docs/amphimixis-ai.md`
5. `amphimixis-integrations/ai-system-doc.md`
6. `amphimixis-integrations/opencode/opencode-implementation.md`

## Rules

1. If you change uncommited files, commit them before.
2. Commit your changes for versioning.
3. Check CI pass, run the `ci/runner.sh` script.

## Actions

- To regenerate Amphimixis agents call `agents-regenerator` at `.opencode/agents/agents-regenerator.md`.
- To create command, understand that the CLI commands are located in `amphimixis/amixis/commands/`; complex commands are combined into one module directory: `add`, `opencode`, etc; the commands haves the examples and main examples in `amphimixis/amixis/parser.py`; the commands are called from `amphimixis/amixis/__main__.py`; `amphimixis/amixis/utils` contains general tools for creating commands; the commands changing requires changes of documentation and examples.

## Commits and PR Titles

Use conventional commit-style messages and PR titles: type(scope): summary.

Valid types are `feat`, `fix`, `docs`, `chore`, `refactor`, and `test`. Scopes are optional.
Examples: `fix(amixis.commands.opencode.install): fix path to amixis`, `docs: update contributing guide`, `chore: update .gitignore`.

Use feature-branches to developing, don't commit to `main`.

## Style Guide

### General principles

- Use PEP 8 and Google TypeScript style guides.
- Use `pathlib.Path` instead of `os.path` for Python.
- Keep project structure.
- Modules are called as workers: `analyzer`, `profiler`, `perf_analyzer`.
- Use return codes instead of exceptions as possible.
- Modules must have a public API via `all` in `__init__.py`, if module is complex, otherwise use underscore in the name, e.g. `_print_with_decorators()` -- not in API.
- Prefer OOP and design patterns.
- The imports must be at the top of the file.

### Complex Logic

When a function has several validation branches or supporting details, make the main function read as the happy path and move supporting details into small helpers below it.
