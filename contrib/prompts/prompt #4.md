# Task: Cross-Compile, Test, and Profile `jq` for RISC-V64, Then Recommend Optimal Build Flags

## Context

You are tasked with cross-compiling the `jq` project for a RISC-V64 target board, validating correctness, profiling performance under several optimization flag combinations, and producing a data-backed recommendation for the best flag set.

## Target Environment

- **Architecture:** RISC-V64 (`riscv64`)
- **March string:**
  `rv64imafdcv_zicbom_zicboz_zicntr_zicond_zicsr_zifencei_zihintpause_zihpm_zfh_zfhmin_zca_zcd_zba_zbb_zbc_zbs_zkt_zve32f_zve32x_zve64d_zve64f_zve64x_zvfh_zvfhmin_zvkt_sscofpmf_sstc_svinval_svnapot_svpbmt`
- **Board access:** `root@192.168.100.2` via SSH, no password required (keys/config already in place).

## Step-by-Step Instructions

### 1. Set Up Cross-Compilation
- Configure a RISC-V64 cross-compilation toolchain (e.g., `riscv64-unknown-linux-gnu-gcc` or equivalent) targeting the exact `march` string above.
- Confirm the toolchain accepts the full extension string without falling back to a generic `rv64gc` baseline.

### 2. Build Multiple Optimization Variants
Produce **separate builds** of `jq`, each combining different optimization flags, for example:
- `-O2`
- `-O3`
- `-O3 -flto`
- `-O2 -flto`
- Any other meaningful combination (e.g., adding `-march=native`-equivalent tuning, `-funroll-loops`, etc.) worth comparing.

**Requirements for every build:**
- Always include `-g` (debug symbols) regardless of optimization level, so profiling tools can resolve symbols.
- Use the exact `-march=` string provided above for every build.
- Keep builds cleanly separated (distinct output directories/binaries) so each variant can be tested and profiled independently without overwriting others.

### 3. Deploy to the Board
- Copy all built `jq` binaries (and any required test assets/inputs) to the board at `root@192.168.100.2`.
- Verify the binaries are executable on the target (correct architecture, no missing shared libraries).

### 4. Run Functional Tests
- Execute the project's test suite on the board using `jq`, invoking tests via:
  `jq tests/<test_name>`
- Run this for **each build variant**.
- Confirm all tests **pass** before moving to profiling. Do not profile a variant that fails tests — fix or note the failure first.

### 5. Research Before Profiling
- Before designing the profiling methodology, review `x86-64-report.md` (an existing report, presumably from a prior x86-64 profiling exercise) to reuse its methodology, metrics, and command patterns as a baseline/reference for consistency.

### 6. Profile Each Build Variant
- Pin every profiling run to a single core using `taskset -c N` (pick a consistent core `N` across all runs for comparability).
- Profile:
  - The test suite runs.
  - A benchmark workload: `jq test_input_large.json` (or the appropriate command form for a large-input benchmark).
- Collect the following hardware/performance counters for every run (e.g., via `perf stat`):
  - **cycles**
  - **instructions**
  - **cache-references**
  - **cache-misses**
  - **branch-misses**
  - **page-faults**

### 7. Analyze Results
- Compare metrics across all flag combinations.
- Identify which combination performs best overall (fewest cycles/instructions, best cache behavior, lowest branch-misses, etc.), and explain **why** — tie the explanation back to what each flag does (e.g., LTO enabling better inlining/cross-TU optimization, `-O3` enabling vectorization on the `v`/`zve*` extensions present in this march, etc.).
- Note any trade-offs (e.g., larger binary size, longer build time, marginal gains).

### 8. Produce the Report
Create `riscv-report.md` and place it in the `jq` project directory on the host. It must include:
- **Runs:** the exact commands used for each build, each test invocation, and each profiling run (fully reproducible).
- **Metrics:** the raw collected counters (cycles, instructions, cache-references, cache-misses, branch-misses, page-faults) for every build variant, for both the test suite and the benchmark.
- **Analysis:** a clear conclusion on which flag combination is best, with reasoning grounded in the collected data and the RISC-V extensions available on this target.

## Deliverable

A single file: **`riscv-report.md`**, saved in the `jq` directory, containing build commands, test results, profiling metrics, and the final flag-combination recommendation with justification.
