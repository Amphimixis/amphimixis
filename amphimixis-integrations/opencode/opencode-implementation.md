# Amphimixis-AI Opencode implementation

This document describes how the Amphimixis-AI agent system (see [ai-system-doc.md](../ai-system-doc.md)) is implemented for Opencode: the directory layout, the tools, the plugins, and the inspecting method. Agents are markdown definition files describing the roles from the agent system in general; tools are TypeScript wrappers under which the `amixis` CLI works.

## Table of Contents

- [Directory structure](#directory-structure)
- [Installed layout](#installed-layout)
- [Plugins and the inspecting method](#plugins-and-the-inspecting-method)
- [Tools reference](#tools-reference)

---

## Directory structure

```
amphimixis-integrations/
├── ai-system-doc.md       <- general info about the agent system (implementation-agnostic)
├── inspector_general/      <- report inspector package (shared, single source)
└── opencode/
    ├── opencode-implementation.md
    ├── agents/             <- agent definitions
    │   ├── amphimixis.md              orchestrator of following subagents
    │   ├── amphimixis-analyzer.md     repository analyzer
    │   ├── amphimixis-configurator.md config writer (create or edit `amixis` config file)
    │   ├── amphimixis-builder.md      build & test runner
    │   ├── amphimixis-profiler.md     performance profiler
    │   └── amphimixis-optimizer.md    optimization recommender
    ├── tools/              <- TypeScript wrappers under which the `amixis` works and other tools
    │   ├── amphimixis-analyze.ts
    │   ├── amphimixis-analyze-vectorization.ts
    │   ├── amphimixis-build.ts
    │   ├── amphimixis-configure-platforms.ts
    │   ├── amphimixis-configure-recipes.ts
    │   ├── amphimixis-configure-builds.ts
    │   ├── amphimixis-profile.ts
    │   ├── amphimixis-validate.ts
    │   └── calculate-optimization-improvement.ts
    ├── plugins/            <- opencode plugins
    │   └── amphimixis-inspector.ts
    ├── commands/           <- opencode commands
    │   └── amphimixis-inspect-session.md
    └── __tests__/          <- LLM-tools tests
        ├── analyzing_test.ts
        ├── building_test.ts
        ├── configuring_test.ts
        ├── profiling_test.ts
        ├── validating_test.ts
        └── inspector_test.ts
```

Every agent file in `agents/` is a markdown definition that carries an `amphimixis-ai version` frontmatter field per the [versioning scheme](../ai-system-doc.md#versioning) of the agent system.

## Installed layout

`amixis opencode install` copies the above into the Opencode config directory.
The plugin dynamically resolves `inspector_general` at runtime — it is
installed as a declared node package in the config directory.

Install registers the committed `amphimixis-integrations/inspector_general/`
package with `bun add "file:<project>/amphimixis-integrations/inspector_general"`.
This adds `inspector_general` to the config `package.json` and `bun.lock`, so
neither Opencode's own dependency reinstall nor `bun prune` removes it from
`node_modules`. The plugin resolves it as
`import InspectorGeneral from 'inspector_general'`.

Tools call `amixis` as a subprocess. The `amixis` executable path is written
into the installed tools at install time (via the `$AMIXIS_PATH` template
substitution).

---

## Plugins and the inspecting method

The report and session inspection is implemented in Opencode by two artifacts plus shared logic: the `amphimixis-inspector` plugin, the `amphimixis-inspect-session` command, and the shared `inspector_general` package.

### `inspector_general` package — formal report inspection

Shared report-inspection logic (not Opencode-specific) that checks the correctness of the improvements and cross-tables data in the report file:

- reads the `improvements.json` file and the `cross-tables/CT-*.md` files produced by the tools;
- verifies the report's improvements table — heading must contain "Improvement", at least 4 columns in strict order (`Measured | Baseline value | Optimized value | Improvement %`), rows copied verbatim from `improvements.json`;
- verifies each cross-table — exactly 4 columns in strict order (`Symbol | {First build name} % | {Second build name} % | Delta %`), copied unchanged from the corresponding `cross-tables/CT-*.md` file;
- checks that required data sources exist (cross-tables via `amphimixis-compare`, improvements via `calculate-optimization-improvement`, the report file itself) and reports missing steps otherwise.

It is installed to the Opencode config directory as the declared `inspector_general` node package (a committed `file:` dependency into the repository) and resolved at runtime by the plugin.

### `amphimixis-inspector` plugin

The `plugins/amphimixis-inspector.ts` plugin hooks the Opencode event stream (`message.part.updated`) and performs two kinds of inspection:

- **Subtask session inspection**: when a `task` tool call to an `amphimixis-*` subagent (other than `amphimixis-inspector`) completes, the whole subagent session is collected into a script (exported via `opencode export <sessionID>`), written to `.inspected-session-<session ID>`, and the `amphimixis-inspect-session` command is run on it in the parent session.
- **Main session inspection**: when a step finishes and the last message matches `WORK ON THE .*? IS COMPLETED`, the main session is inspected the same way, and additionally the shared `InspectorGeneral.inspect()` runs against the report. If the formal inspection fails, a prompt is sent to the orchestrator agent to check itself to completing all tasks (up to a maximum number of formal inspection attempts per session).

The plugin tracks a per-session inspection status (`NOT_INSPECTED`, `OK`, `TO_FIX`): a session is marked `OK` when the inspecting command output contains `INSPECTION IS PASSED`; otherwise it stays in the `TO_FIX` state and can be re-inspected on the next completion.

### `amphimixis-inspect-session` command

The `commands/amphimixis-inspect-session.md` command is most simple legal method to delegate task to subagent (native subtask delegation) and call it from code, in this case, orchestrator delegates checking to plan agent that reads the first string of `.inspected-session-<session ID>` to learn the inspected agent (defaults to `amphimixis`), then acts situationally:

- for every agent — the agent must not write the tool-owned files (`CT-*.md`, `improvements.json`, `<project name>.json`) by itself, and all actions must run in the current directory;
- for `amphimixis-builder` and `amphimixis-profiler` — the project must have been built and profiled for all machines; build and run machine info comes from the config file (usually `input.yml`): `platforms` lists machine info, `build_machine` and `run_machine` reference platform IDs;
- for `amphimixis-profiler` — the profiler must not falsify profiling data from tools.

---

## Tools reference

| Tool                             | Action                                                               |
|----------------------------------|----------------------------------------------------------------------|
| amphimixis-analyze               | Run `amixis analyze /path/to/project`                                |
| amphimixis-analyze-vectorization | Run `amixis analyze -v /path/to/project`                             |
| amphimixis-build                 | Run `amixis build /path/to/project`                                  |
| calculate-optimization-improvement | Calculate improvement `(optimizedValue / baselineValue) * 100` formally (not by LLM) and append the record to `improvements.json` |
| amphimixis-configure-platforms   | Add new platforms to the `platforms` field in the amixis config file |
| amphimixis-configure-recipes     | Add new recipes to the `recipes` field in the amixis config file     |
| amphimixis-configure-builds      | Add new builds to the `builds` field in the amixis config file       |
| amphimixis-profile               | Run `amixis profile /path/to/project`                                |
| amphimixis-validate              | Run `amixis validate /path/to/config/file`                           |
