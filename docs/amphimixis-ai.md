# Amphimixis-AI

Amphimixis-AI helps you analyze your project for migration ability — __it automates this process__. It provides an agent system and formal tools for Opencode:

- `Amphimixis` — orchestrator agent, and subagents which are called by the orchestrator
- Tools — wrappers around the `amixis` CLI and other tools

---

## Table of Contents

- [Usage](#usage)
- [Pipeline](#pipeline)
- [Versioning](#versioning)
- [Tool reference](#tool-reference)
- [Installation](#installation)
- [Running the tests](#running-the-tests)

---

## Usage

Bare `amixis opencode` opens the Opencode TUI with the `amphimixis` agent.

For non-interactive runs, use the `run` subcommand. It runs `opencode` non-interactively and prints only the text messages produced by the session (requires `jq`):

```bash
amixis opencode run "Analyze the <Name> project, identify platform-specific code, and produce a migration report for RISC-V. Use my cross-toolchain /path/to/toolchain."
```

To skip processing and print the raw session output, add `--no-processing-output` (no `jq` needed):

```bash
amixis opencode run --no-processing-output "Analyze the <Name> project, identify platform-specific code, and produce a migration report for RISC-V. Use my cross-toolchain /path/to/toolchain."
```

> **Note:** The agent expects the current working directory to contain (or point to) the project being analyzed. Use an absolute path in the prompt for clarity.

---

## Pipeline

When invoked, `amphimixis` runs a 7-phase pipeline:

| Phase                                       | Worker                       | Description                                                                                           |
|---------------------------------------------|------------------------------|-------------------------------------------------------------------------------------------------------|
| 1. Repository analysis                      | `amphimixis-analyzer`        | Find the actual repo, clone it, scan for platform-specific macros and intrinsics, assess dependencies |
| * Session of previous agent inspection      | `amphimixis-inspect-session` | Do nothing                                                                                            |
| 2. Configuration                            | `amphimixis-configurator`    | Create the `input.yml` (see [Usage Guide](usage_guide.md)) file with platforms, recipes, and builds   |
| * Session of previous agent inspection      | `amphimixis-inspect-session` | Do nothing                                                                                            |
| 3. Build & verify                           | `amphimixis-builder`         | Build on reference and target platforms, run tests                                                    |
| * Session of previous agent inspection      | `amphimixis-inspect-session` | Inspect session for errors in work                                                                    |
| 4. Profiling                                | `amphimixis-profiler`        | Profile executables, produce a cross-platform comparison                                              |
| * Session of previous agent inspection      | `amphimixis-inspect-session` | Inspect session for errors in work                                                                    |
| 5. Optimization                             | `amphimixis-optimizer`       | Analyse bottlenecks and suggest improvements                                                          |
| * Session of previous agent inspection      | `amphimixis-inspect-session` | Inspect session for errors in work                                                                    |
| 6. Repeat pipeline                          | `amphimixis`                 | Apply optimizations, rebuild, re-profile, compare before/after                                        |
| 7. Final report                             | `amphimixis`                 | Compile a structured report by the [Report Template](./report-template.md)                |
| * Session of orchestrating agent inspection | `amphimixis-inspect-session` | Inspect session for errors in work                                                                    |

The agent hierarchy follows a strict delegation pattern:

```
amphimixis (orchestrator)          mode: all
│   delegates work, never calls tools directly
│
├── amphimixis-analyzer            mode: subagent
│   └── uses: amphimixis-analyze.ts, amphimixis-analyze-vectorization.ts
|
├── * amphimixis-inspect-session   command (run plan agent)
│
├── amphimixis-configurator        mode: subagent
│   └── uses: amphimixis-configure-platforms.ts,
│             amphimixis-configure-recipes.ts,
│             amphimixis-configure-builds.ts,
│             amphimixis-validate.ts
|
├── * amphimixis-inspect-session   command (run plan agent)
│
├── amphimixis-builder             mode: subagent
│   └── uses: amphimixis-build.ts
|
├── * amphimixis-inspect-session   command (run plan agent)
│
├── amphimixis-profiler            mode: subagent
│   └── uses: amphimixis-profile.ts,
│             amphimixis-analyze-vectorization.ts
|
├── * amphimixis-inspect-session   command (run plan agent)
│
└── amphimixis-optimizer           mode: subagent
|   └── uses: amphimixis-analyze-vectorization.ts
|
└── * amphimixis-inspect-session   command (run plan agent)
```

Each subagent receives structured context from its predecessor and passes results forward. The orchestrator validates completeness after each phase before proceeding.

---

## Versioning

The agent system is versioned to make generated artifacts reproducible and traceable back to the methodology that produced them.

Three components carry a SemVer-like `<major>.<minor>.<patch>` version:

| Component            | Where it lives                                                          |
|----------------------|-------------------------------------------------------------------------|
| Methodology          | `> **Version**: …` in the methodology document                           |
| Regeneration pipeline | one shared version for `agents-regenerator` and `migration-expert`, in the `regeneration-pipeline version` frontmatter field of each definition |

Segment meanings (like SemVer): **major** — structural change / reorganization / full regeneration; **minor** — new feature / update; **patch** — small change, bug fix, correction, hand-made change.

Every generated agent carries an `amphimixis-ai version` field with three dash-separated segments:

```
<methodology ver.>-<regeneration-pipeline ver.>-<regen count>.<hand-made patch>
```

- The first two segments record the fixed versions of the methodology and regeneration pipeline that generated the agent.
- The last segment is the concrete agent's own version: its first slot bumps on each regeneration, its second slot bumps on hand-made (manual, out-of-regeneration) corrections.
- When the methodology or the regeneration-pipeline version changes, the last segment resets to `1.0`.

Current values: methodology `0.1.0`, regeneration pipeline `0.1.0`, and a freshly generated agent is `amphimixis-ai version: 0.1.0-0.1.0-1.0`.

---

## Tool reference

All tools are defined as TypeScript files using `@opencode-ai/plugin`.

| Tool                                  | Action                                                     | Purpose |
|---------------------------------------|------------------------------------------------------------|---------|
| `amphimixis-analyze.ts`               | Run `amixis analyze <path>`                                | Detect build systems, test frameworks, CI, documentation, dependencies |
| `amphimixis-analyze-vectorization.ts` | Run `amixis analyze -v <arch> <binary>`                    | Scan a binary for platform-specific vector instructions (SSE, AVX, AVX-512, NEON, RVV) |
| `amphimixis-build.ts`                 | Run `amixis build <path> [--config] [--build-name]`        | Build the project using a specific configuration |
| `amphimixis-configure-platforms.ts`   | Add platforms to `platforms` field in `amixis` config file | Add machine definitions to `input.yml` with auto-assigned IDs |
| `amphimixis-configure-recipes.ts`     | Add recipes to `recipes` field in `amixis` config file     | Add build recipes (flags, toolchain, sysroot) to `input.yml` |
| `amphimixis-configure-builds.ts`      | Add builds to `builds` field in `amixis` config file       | Link platforms and recipes into executable build tasks |
| `amphimixis-profile.ts`               | Run `amixis profile <path> [--config] [--build-name]`      | Profile executables with `perf stat` and `perf record` |
| `amphimixis-validate.ts`              | Run `amixis validate <config>`                             | Validate an `input.yml` configuration file |

The configure tools write YAML directly rather than calling the CLI — they manipulate `input.yml` programmatically.

---

## Installation

### Requirements

- A working `amixis` installation (see [Usage Guide](usage_guide.md#choose-an-installation-method))
- `amixis` must be on `PATH` (tools invoke `amixis` as a subprocess)
- The Opencode CLI (`opencode`) installed and available on `PATH`
- `bun` for installing test/utility dependencies
- `jq` for `amixis opencode run` text-only processing (installed automatically into the Opencode config dir with `amixis opencode install` via the `node-jq` package, or install it from <https://jqlang.org>; skip with `--no-processing-output`)

### Install the agents and tools

```bash
amixis opencode install
```

This copies agents, tools, commands, and plugins into the local `.opencode/` directory, writes the `amixis` executable path into the installed tools, and installs Bun dependencies (including `node-jq`, which ships the `jq` binary used by `amixis opencode run`).

For a system-wide installation, pass the `--global` flag:

```bash
amixis opencode install --global
```

This installs into `$XDG_CONFIG_HOME/opencode` (defaults to `~/.config/opencode`).

### Uninstall

```bash
amixis opencode uninstall
amixis opencode uninstall --global
```

Removes only the files that were placed by `install` and the declared
`inspector_general` dependency (via `bun remove`, including its `package.json`
and `bun.lock` entries). Leaves the remaining `package.json`/`bun.lock`
entries, `opencode.json(c)`, and any user-owned files untouched.

---

## Running the tests

Tests use **Bun's built-in test runner** (`bun:test`). They reside in `amphimixis-integrations/opencode/__tests__/`.

```bash
cd amphimixis-integrations/opencode
bun test
```
