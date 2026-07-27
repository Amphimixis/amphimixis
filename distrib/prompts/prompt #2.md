# Cross-Platform Build, Test & Performance Analysis Task

## Context

- **Host (current) architecture:** x86-64
- **Target architecture:** RISC-V 64
- **Target `-march` string:**
  ```
  rv64imafdcv_zicbom_zicboz_zicntr_zicond_zicsr_zifencei_zihintpause_zihpm_zfh_zfhmin_zca_zcd_zba_zbb_zbc_zbs_zkt_zve32f_zve32x_zve64d_zve64f_zve64x_zvfh_zvfhmin_zvkt_sscofpmf_sstc_svinval_svnapot_svpbmt
  ```

You are working on a project that needs to be built, tested, profiled, and analyzed on **both** x86-64 (native) and RISC-V 64 (cross-compiled / emulated) targets.

---

## 1. Preparation

- Check and record all relevant environment variables before starting any build (toolchain paths, compiler versions, cross-compiler prefix, `QEMU_LD_PREFIX`, etc.).

## 2. Build

- Produce several builds by combining the following optimization flags:
  - `-O3`
  - `-O2`
  - `-flto`
  - `-fno-vectorization` (i.e. run separate builds mixing/toggling these flags rather than a single combined flag set)
- Every build, regardless of optimization flags, must also include `-g` (debug symbols).
- Build for **both** platforms:
  - Native x86-64
  - Cross-compiled RISC-V 64 using the `-march` string above
- Place all resulting build artifacts in `./build` (organize by platform and flag combination, e.g. `./build/x86-64/O3/`, `./build/riscv64/O2-flto/`, etc.).

## 3. Test

- Run tests using `jq` directly against the test files, e.g. `jq tests/<test_name>`.
- **Do not use `make` to run tests** — invoking `make` triggers an unwanted recompilation.
- Confirm that all tests pass for every build variant on both platforms before moving to profiling.

## 4. Profile

- Pin each profiled process to a single core using `taskset -c N`.
- Profile test runs on **both** platforms:
  - x86-64: run natively.
  - RISC-V 64: run under emulation using `qemu` (via `qemu-binfmt`, which is already installed).
- Collect the following hardware/performance counters for each run:
  - Cycles
  - Instructions
  - Cache references
  - Cache misses
  - Branch misses
  - Page faults
- Save all profiling output into `./profiling`, organized so results are traceable back to platform, build flags, and test name.

## 5. Analyze

- Build cross-platform performance comparisons (x86-64 vs RISC-V 64) across the different build flag combinations.
- Analyze vectorization differences between builds/platforms (especially `-fno-vectorization` vs. vectorized builds, and use of the RISC-V vector extension `v`/`zve*`/`zvfh*` flags).
- Provide a causal analysis explaining **why** the observed metrics differ between platforms and build configurations (e.g. microarchitectural differences, ISA extension usage, compiler codegen differences, cache/memory hierarchy effects).
- Suggest possible optimizations:
  - Cross-platform optimizations applicable to both targets.
  - RISC-V–specific optimizations (e.g. leveraging specific extensions present in the target `-march`, such as `v`/vector extensions, bit-manipulation `zb*` extensions, crypto `zk*` extensions, etc.).

## 6. Deliverables

- Save all findings in `./reports`, split across multiple files by content area, for example:
  - `./reports/build-summary.md`
  - `./reports/test-results.md`
  - `./reports/profiling-results.md`
  - `./reports/cross-platform-comparison.md`
  - `./reports/vectorization-analysis.md`
  - `./reports/optimization-recommendations.md`
