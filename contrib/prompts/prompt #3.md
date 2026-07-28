# Task: Build, Profile, and Compare jq Compiler Optimization Flags

## Objective
Determine which combination of compiler optimization flags produces the best-performing build of the `jq` project, using empirical profiling data (not assumptions).

## Steps

### 1. Build Variants
- Build the project multiple times, each with a different combination of optimization flags (e.g. `-O2`, `-O3`, `-flto`, and other relevant combinations).
- **Every build must include the `-g` flag** (debug symbols), even in optimized builds, so profiling tools can resolve symbols correctly.
- Keep each build's binary/output separate and clearly labeled by its flag combination.

### 2. Run Correctness Tests
- Run tests using `jq` directly against test files:
  ```
  jq tests/<test_name>
  ```
- **Do not run tests via `make`** — this triggers an unwanted recompilation step.
- Confirm all tests pass for **every** flag combination before profiling it. Do not profile a build that fails correctness tests.

### 3. Profile Each Build
- Pin each profiling run to a single CPU core for consistent measurements:
  ```
  taskset -c N <command>
  ```
- Profile both:
  - The test suite runs
  - A large benchmark input:
    ```
    jq test_input_large.json
    ```
- For each run, collect the following hardware performance counters:
  - Cycles
  - Instructions
  - Cache references
  - Cache misses
  - Branch misses
  - Page faults

### 4. Analyze Results
- Compare metrics across all flag combinations.
- Identify which combination performs best overall.
- Explain **why** that combination wins (e.g. instructions-per-cycle, cache behavior, inlining effects from LTO, etc.) — don't just report numbers, interpret them.

### 5. Produce `report.md`
Write a report to `report.md` containing:
- **Runs**: exact commands used for each build and each profiling run (fully reproducible).
- **Metrics**: raw performance counter results for each flag combination.
- **Analysis**: which flag combination is best, and the reasoning behind that conclusion, grounded in the collected metrics.

## Constraints
- Test execution must go through `jq`, never `make`.
- All builds must retain debug symbols (`-g`).
- Profiling must be pinned to a single core via `taskset`.
- Conclusions must be backed by the actual collected data, not general assumptions about optimization flags.
