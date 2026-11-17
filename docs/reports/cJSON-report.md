# Amphimixis Migration Readiness Report — cJSON

**Reference platform:** x86_64 (local container)  
**Target platform:** riscv64 (cross-compiled, executed under `qemu-riscv64-static` user-mode emulation)  
**Project version:** cJSON v1.7.19 (commit `6d9f2443ab071f86e5d9b43025a40929ec41c46c`)  
**Pipeline:** Amphimixis methodology steps 1–6; report date 2026-10-03

---

## 1. Repository & Project Status

| Item | Value |
|---|---|
| Repository URL | `https://github.com/DaveGamble/cJSON.git` |
| Active repository resolved | DaveGamble/cJSON (official upstream; not archived; ~13,020 stars, 3,525 forks, MIT) |
| Cloned to | `/work/cJSON-workspace/cJSON` (branch `master`, clean tree) |
| Latest commit | `6d9f2443ab071f86e5d9b43025a40929ec41c46c` — 2026-09-16 ("Fix: heap-use-after-free in merge_patch ... (#1065)") |
| Total commits | 1,113 |
| Latest tag | `v1.7.19` (2025-09-09); 49 tags total; recent: v1.7.19, v1.7.18 (2024-05-13), v1.7.17 (2023-12-26) |
| Activity | Actively maintained (latest upstream push ~17 days before analysis; recent security fixes #1065, #1006, #991, #984) |
| Top contributors | Max Bruckner (720), Dave Gamble (85), Alanscut (80), Alan Wang (33) |
| Build systems | CMake (`CMakeLists.txt`, min 3.5 per Debian patch) and GNU Make (`Makefile`). No `meson.build` on master (stale `origin/meson` branch only) |
| Tests | ~163 `RUN_TEST` cases across 21 files → 18 Unity test executables + utils/patch; CTest reports **19 tests**; **153 Unity assertions** |
| Test framework | Unity (vendored in-tree at `tests/unity/`, architecture-neutral C) |
| External dependencies | **None** for the library. Only C standard headers + `libm` (linked on non-Windows). Test/dev extras: bundled Unity, optional Valgrind, optional OSS-Fuzz/libFuzzer |
| Benchmarks | None found (analyzer: `benchmarks: []`) |
| CI | GitHub Actions `.github/workflows/CI.yml` (ubuntu-latest + macos-latest; GCC/Clang × valgrind/sanitizers/none) and `ci-fuzz.yml`; legacy Travis/AppVeyor. **No non-x86 / RISC-V / QEMU CI job** |
| Docs | `README.md` (27 KB), `CHANGELOG.md` (26 KB), `CONTRIBUTORS.md`, `SECURITY.md`, LICENSE |
| Distro packages | Debian: `libcjson-dev` / `libcjson1` (`Architecture: any`), trixie `1.7.18-3.1+deb13u1` and unstable `1.7.19-2+b1` **include riscv64**; Arch `extra/cjson 1.7.19-1` (x86_64, RISC-V port not confirmable); OpenEmbedded/Yocto `cjson_1.7.19.bb`; Repology 183 entries across many distros |
| Project size | ~5.1 MB checkout; `cJSON.c` 3,206 LOC, `cJSON.h` 306, `cJSON_Utils.c` 1,485, `cJSON_Utils.h` 88 |

**Forks with RISC-V patches:** Checked — GitHub forks, repo search (`cJSON riscv`), and upstream issue/PR search returned **0** RISC-V-related forks/PRs/issues; no arch branch exists. This is expected: the codebase has zero architecture-specific code, so no port patches are required.

---

## 2. Platform-Specific Code Analysis

### Architecture macros
**None found.** An exhaustive scan for x86 (`__x86_64__`, `__i386__`, `_M_X64`, `__SSE*`, `__AVX*`, `__FMA__`, `__BMI*`, `__POPCNT__`), ARM (`__aarch64__`, `__arm__`, `__ARM_NEON`, `__ARM_FEATURE*`), RISC-V (`__riscv*`), endianness (`__BYTE_ORDER__`, `__LITTLE_ENDIAN__`), and pointer-size (`__LP64__`, `__ILP32__`) macros returned **zero matches**.

### Platform preprocessor guards
| Guard | File:Line | Platform / semantics | Scope |
|---|---|---|---|
| `_MSC_VER` / `_CRT_SECURE_NO_DEPRECATE` | cJSON.c:27,34,52,163; cJSON_Utils.c:24,31,46 | MSVC only | Deprecation macro, warning pragmas, dllimport malloc/free wrappers |
| `__GNUC__` | cJSON.c:31,55,2069; cJSON.h:74 | GCC | visibility pragmas, `-Wcast-qual` suppression |
| `__clang__` / `__GNUC__` version test | cJSON.c:2066,2077 | Clang/GCC>4.5 | diagnostic push/pop around `cast_away_const` |
| `_WIN32` | cJSON.c:81 | Windows | `NAN` = `sqrt(-1.0)` vs `0.0/0.0` |
| `__WINDOWS__`, `WIN32`, `WIN64`, `_MSC_VER`, `_WIN32` | cJSON.h:31,35 | Windows | calling conventions, `__declspec(dllexport/dllimport)` |
| `CJSON_HIDE/IMPORT/EXPORT_SYMBOLS` | cJSON.h:59,63,65,67 | feature flag | symbol visibility mode |
| `__GNUC__` / `__SUNPRO_CC` / `__SUNPRO_C` / `CJSON_API_VISIBILITY` | cJSON.h:74 | GCC/Solaris | `__attribute__((visibility("default")))` |
| `__cplusplus` | cJSON.h:26,302; cJSON_Utils.h:26,84 | C++ | `extern "C"` linkage |
| `ENABLE_LOCALES` | cJSON.c:48,281 | feature flag | optional `locale.h` include/use (off by default) |
| `true`/`false`/`isinf`/`isnan`/`NAN` | cJSON.c:62,67,73,76,80 | C90-vs-C99 | ANSI-C fallbacks |
| **`__GNUCC__`** (misleading) | **cJSON_Utils.c:28,49** | **typo for `__GNUC__`** | GCC visibility pragmas never emitted in that TU |
| `__WIN32__` / `__TMS470__` | tests/unity/... | Windows / TI ARM | vendored Unity only |

### Portability verdict
| Aspect | Verdict |
|---|---|
| No exceptions (`throw`, `setjmp`, `pthread`, `thread_local`) | ✅ None — C89, safe for `-fno-exceptions`/no-runtime |
| Alignment safety | ✅ No pointer punning, no casts of char buffers to `int`/`double`/`long`, no `#pragma pack`, no unaligned loads/stores, no union type-punning; numeric conversion via `strtod`/`sprintf`; endian-neutral |
| Embedded usability | ✅ Single `.c`+`.h`, ANSI C89, no external deps, caller-supplyable allocator hooks (`cJSON_Hooks`/`cJSON_InitHooks`), configurable nesting/circular limits |
| Overall portability level | **LOW** (architecture-agnostic; no source-level porting work anticipated for riscv64) |

### Vectorization intrinsics in source
**None.** `_mm_*`/`_mm256_*`/`_mm512_*`, `arm_neon.h`/`vld1*`/`vaddq*`, `riscv_vector.h`/`__riscv_v*`, and inline asm (`__asm`, `asm volatile`) all returned **zero matches**. Only compiler auto-vectorization is possible.

---

## 3. Build & Test Results

| Platform | Build dir | Build status | Method | Binary (ELF arch) | Tests | Result |
|---|---|---|---|---|---|---|
| Reference x86_64 | `/work/cJSON-workspace/x86-build` | **SUCCESS** | `amixis build` FAILED → manual CMake fallback | `x86-build/cJSON_test` — ELF64 x86-64 | `ctest` 19/19 | **19 passed, 0 failed** (153 Unity assertions, 1 ignored) |
| Target riscv64 | `/work/cJSON-workspace/riscv-build` | **SUCCESS** | `amixis build` FAILED → manual cross CMake fallback | `riscv-build/cJSON_test` — ELF64 RISC-V | 19 test executables run under QEMU | **19 passed, 0 failed** (exits 0) |
| Reference (optimized) x86_64 | `/work/cJSON-workspace/x86-build-opt` | **SUCCESS** | corrected `-O3` CMake build | `x86-build-opt/cJSON_test` | `ctest` 19/19 | **19 passed, 0 failed** |
| Target (optimized) riscv64 | `/work/cJSON-workspace/riscv-build-opt` | **SUCCESS** | corrected `-O3` cross CMake build | `riscv-build-opt/cJSON_test` | 19 under QEMU | **19 passed, 0 failed** |

### Build/test failures detail
- **`amixis build`/`amixis profile` failed for BOTH builds** (exit 1: `[Config] ✗ Failed to create build`). Root cause in `amphimixis.log`: `CONFIGURATOR | ERROR | Invalid local machine arch: riscv, your machine is x86_64`. amixis 0.2.0 treats the address-less riscv platform as the local x86_64 machine and aborts the whole config, including the pure-x86 `1_1_1` build. Manual fallback was used for both platforms.
- **RISC-V `ctest` failed (19/19)** because `CMAKE_CROSSCOMPILING_EMULATOR` is not honored when host and target `CMAKE_SYSTEM_NAME` are both Linux (`CMAKE_CROSSCOMPILING` stays FALSE); the bare RISC-V ELF was launched by `binfmt_misc` without the `-L /usr/riscv64-linux-gnu` sysroot (`Could not open '/lib/ld-linux-riscv64-lp64d.so.1'`). All 19 binaries pass when run explicitly via `qemu-riscv64-static -L /usr/riscv64-linux-gnu`.
- `-DBUILD_TESTING=ON` is a no-op for cJSON (the real option is `ENABLE_CJSON_TEST`, default ON); tests are nevertheless built.
- The provided target flag `-march=rv64gcvb` is **invalid** for GCC 13 ("ISA string is not in canonical order"); the configurator corrected it to `-march=rv64gcv` (compiles and runs under QEMU).
- `ENABLE_CJSON_UTILS` defaults to OFF, so cJSON_Utils tests were not built.

---

## 4. Performance Comparison

### 4.1 Experimental conditions
| Condition | Value |
|---|---|
| CPU | Intel Core i5-1035G1 @ 1.00 GHz (Ice Lake), 4 physical cores / 8 logical CPUs |
| Caches | L1d 192 KiB, L1i 128 KiB, L2 2 MiB, L3 6 MiB |
| Governor / frequency | `powersave` on all policies; `scaling_cur_freq` ~1.25–1.40 GHz; forcing `performance` **FAILED** (sysfs read-only) |
| Pinning | CPU 2 (`taskset -c 2`) for every warmup/stat/record run, both platforms |
| Priority | `nice -n -20` → **Permission denied**; `chrt` → **Operation not permitted** (no CAP_SYS_NICE); all runs at default nice 0 |
| Warmup | 1 run/platform (identical workload) |
| Measurement runs | `perf stat -r 6` → 6 repeats/platform; `perf record` 1 run/platform |
| `perf_event_paranoid` | -1 (running as root) |
| Workload | `bench/bench_cjson.c`: builds a deterministic 36,432-byte nested JSON (200 items), then per iteration `cJSON_Parse` + `cJSON_PrintUnformatted` + delete; checksum `36528000` identical on both platforms |
| Iterations | 1000 (perf stat), 2000 (perf record) |
| Emulator | `qemu-riscv64-static` 8.2.2, single-threaded TCG, `-L /usr/riscv64-linux-gnu` |

### 4.2 Key metrics (measured)
> The riscv64 column is **HOST-SIDE under QEMU emulation** — perf samples the `qemu-riscv64-static` host process (JIT + emulator runtime), **not** guest RISC-V instructions and **not** native RISC-V hardware.

| Metric | x86_64 baseline | x86_64 optimized | riscv64 (QEMU host) baseline | riscv64 (QEMU host) optimized |
|---|---|---|---|---|
| Elapsed time (mean of 6) | 1.68561 s | 1.6009 s | 20.2733 s | 19.6477 s |
| task-clock | 1684.97 ms | 1599.48 ms | 20267.68 ms | 19642.43 ms |
| Cycles | 2,303,532,853 | 2,179,342,513 | 27,787,365,347 (host) | 26,908,386,567 (host) |
| Instructions retired | 7,662,840,791 | 7,356,591,621 | 95,394,076,406 (host) | 91,832,156,056 (host) |
| IPC (insn/cycle) | 3.33 | 3.38 | 3.43 (host) | 3.41 (host) |
| L1-dcache miss rate | 1.95% | 2.04% | 0.41% (host) | 0.42% (host) |
| LLC miss rate | 2.97% | 3.61% | 8.53% (host) | 8.18% (host) |
| Branch misprediction rate | 0.14% | 0.14% | 0.25% (host) | 0.21% (host) |
| cache-miss rate | 2.82% | 3.28% | 9.63% (host) | 9.54% (host) |
| Frontend Bound (TopdownL1) | 30.3% | NOT AVAILABLE | 25.2% (host) | NOT AVAILABLE |
| Backend Bound (TopdownL1) | 2.9% | NOT AVAILABLE | 1.2% (host) | NOT AVAILABLE |
| Retiring (TopdownL1) | 60.5% | NOT AVAILABLE | 62.8% (host) | NOT AVAILABLE |
| Bad Speculation (TopdownL1) | 6.3% | NOT AVAILABLE | 10.9% (host) | NOT AVAILABLE |
| Executable size, stripped `cJSON_test` | 14,472 B | 34,840 B (`bench`) | 10,520 B | 26,744 B (`bench`) |

Topdown percentages for the optimized builds were not measured and are marked **NOT AVAILABLE**; no optimized topdown run exists.

### 4.3 Hotspots — reference platform x86_64 (real `perf record`, `cycles`)
| Self % | Function | Module | Analysis |
|:---:|---|---|---|
| 6.86 | `print_value` | bench_x86 | JSON number formatting path (`__sprintf_chk` 20.5% children) |
| 6.73 | `parse_value` | bench_x86 | recursive parser dispatch (33% children) |
| 5.40 | `malloc` | libc | per-node allocation |
| 5.11 | unresolved libc | libc | internal formatting/mem routines |
| 3.48 | `print_string_ptr` | bench_x86 | string escaping on print |
| 3.15 | `parse_string` | bench_x86 | string scanning |
| 3.15 | `cfree` | libc | node teardown |
| 2.81 | `ensure` | bench_x86 | array growth/realloc |
| 1.86 | `cJSON_Delete` | bench_x86 | recursive free |
| 0.61 | `strlen@plt` | bench_x86 | — |
| 0.59 | `strncmp@plt` | bench_x86 | — |

### 4.4 Hotspots — target platform riscv64
**NOT AVAILABLE for native RISC-V.** Host-side QEMU `perf record` samples are dominated by unresolved JIT addresses (`qemu-riscv64-static` is stripped; top address 7.52%, all `[unknown]`/numeric). No guest-symbol attribution is possible with qemu-user + host perf. Not fabricated.

### 4.5 Bottleneck summary & causal analysis
- **QEMU TCG emulation dominates the 12× gap (primary).** Host instruction count for the emulated run is ~12.45× the native x86 count (95.4 G vs 7.66 G) at essentially equal host IPC (3.43 vs 3.33) — the slowdown comes from executing far more host instructions (translation + dispatch), not from worse host micro-efficiency. RISC-V timing includes emulation overhead and is **not** native RISC-V performance.
- **High Frontend Bound on x86 (30.3%)** with Retiring 60.5% and Backend Bound only 2.9%: cJSON's many small, branchy basic blocks (`parse_value` recursion, `parse_string`, `print_value`) and heavy libc-call footprint limit straight-line fetch; execution cores are not the limit.
- **Allocation + libc formatting are a large share of x86 work.** `malloc` 5.40% self / 11.4% children, `cfree` 3.15%, `__sprintf_chk` ~20.5% children, `__isoc99_sscanf` ~10.2% children. The parse+print workload is allocation- and formatting-bound, not arithmetic-bound.
- **LLC miss rate 2.87× higher on the QEMU side (8.53% vs 2.97%)** and cache-miss rate 3.4× higher — consistent with the emulator's much larger working set (translation cache + guest heap + runtime) exceeding the 6 MiB L3. Host-side; not a guest-cache conclusion.
- **Branch misprediction 1.79× higher on QEMU (0.25% vs 0.14%)** and Bad Speculation 10.9% vs 6.3% — QEMU indirect dispatch/JIT control flow. Host-side.
- **L1-dcache miss rate is lower on the QEMU side (0.41% vs 1.95%)** because the emulator re-executes hot translated blocks from a small footprint; an emulation artifact, not comparable to guest behaviour.
- **Smaller stripped binary on riscv** (`cJSON_test` 0.727×, `bench` 0.809×): RVC compressed instructions vs x86 `-march=native` AVX-512 code. Size is not a runtime bottleneck.
- **Cross-table `[unknown]`:** on x86 most unresolved samples are stripped-libc internals (2,657 libc + 21 kernel of 3,636 cycles); on the QEMU side 100% is unresolved JIT.

### 4.6 QEMU / emulation caveats
- All riscv-side perf numbers are **HOST-SIDE** measurements of the `qemu-riscv64-static` process; they include dynamic binary translation and emulator runtime overhead and are **not** native RISC-V guest counters.
- **Guest RISC-V instruction-level counters cannot be obtained** with qemu-user + host perf; riscv IPC, L1/LLC, branch, and Topdown figures describe the emulator, not the target CPU.
- RISC-V elapsed time includes emulation overhead (~12×) and is not a native-RISC-V measurement.
- The optimized record classifies the libc DSO as `(deleted)`, so libc symbol names appear as `[unknown] (/ (deleted))` (offset-identical to baseline libc frames) — a symbolization artifact, not a performance change.

---

## 5. Optimization Results

### 5.1 Vector instructions in binary
| Build | Executable | Vector count (unique/total) | Concrete mnemonics | Scan tool |
|---|---|---|---|---|
| x86_64 | `x86-build/cJSON_test` | 6 / 18 | `vpinsrq`, `vmovdqa`, `vmovdqu`, `vinserti128`, `vmovupd`, `vmovapd`, `vzeroupper`, `vdivsd` | `amphimixis-analyze-vectorization` + objdump |
| x86_64 | `bench/bench_x86` | 12 / 24 | `vandpd`/`andpd`, `vpinsrq`, `vpxor`, `vmovdqu8`, `vmovdqu`, `vmovdqa`, `vcomisd`, `vmulsd`, `vsubsd`, `vpbroadcastq`, `vpaddq`, `paddq` | `amphimixis-analyze-vectorization` + objdump |
| riscv64 | `riscv-build/cJSON_test` | **0** | none (V ISA enabled but unused) | tool FAILED (exit 1); `riscv64-linux-gnu-objdump` fallback |
| riscv64 | `bench/bench_riscv` | **0** (of 6,962 insns) | scalar RV64GC only (`ld`, `sd`, `mv`, `beqz`, `addi`) | `riscv64-linux-gnu-objdump` fallback |

The x86 "vector" instructions are compiler-generated scalar-SIMD artifacts (`vmovdqu` for `memcpy`/struct moves, `vmovsd`/`vcomisd` for double math), not vectorized hot loops. cJSON's hot loops are byte-at-a-time, pointer-chasing and branch-heavy, so GCC auto-vectorization does not fire on either platform. `Tag_RISCV_arch` = `rv64i_m_a_f_d_c_v1p0+zve*` (V present in ELF attributes) but **zero RVV instructions were emitted**.

### 5.2 Executable size (stripped vs unstripped; strip performed on copies only)
| Binary | Raw unstripped | Raw stripped | Debug/symtab | `.text` |
|---|---:|---:|---:|---:|
| `cJSON_test` x86 | 27,152 B | 14,472 B | 12,680 B | 6,150 B |
| `cJSON_test` riscv | 23,904 B | 10,520 B | 13,384 B | 5,722 B |
| `bench_x86` | 178,952 B | 43,168 B | 135,784 B | 33,383 B |
| `bench_riscv` | 185,688 B | 34,936 B | 150,752 B | 29,016 B |
| `libcjson.so` x86 | 105,768 B | 35,160 B | 70,608 B | 26,481 B |
| `libcjson.so` riscv | 112,056 B | 30,952 B | 81,104 B | 23,636 B |

Raw file size is dominated by DWARF (73–81%). After stripping, RISC-V is consistently smaller (−27% `cJSON_test`, −19% `bench`, −12% `libcjson.so`); `.text` is 7–13% smaller (RVC compression). No code-size/i-cache problem on RISC-V.

### 5.3 Optimization attempts (Before / After / Delta / Causal Analysis)
Applied optimization: **PGO (`-fprofile-generate`/`-fprofile-use -fprofile-correction`) + `-fno-plt` + `-fno-semantic-interposition` + corrected effective `-O3`** on the `bench` workload (obj PGO, same workload `1000 200`, checksum-verified `36528000`).

| Optimization | Before | After | Delta | Causal analysis |
|---|---|---|---|---|
| x86_64 `bench` real_time (s) | 1.68561 | 1.6009 | 94.97 (improvementPcnt) | PGO re-lays-out hot branches/cold paths; fewer cycles and instructions; modest gain because the hot set (scalar parse/print + libc allocation) is unchanged |
| x86_64 `bench` IPC | 3.33 | 3.38 | 101.50 | Better code layout/inlining raises instructions-per-cycle slightly |
| x86_64 `bench` cycles | 2303532853 | 2179342513 | 94.61 | ~5.4% fewer cycles, driven by PGO layout and `-fno-plt` |
| x86_64 `bench` instructions | 7662840791 | 7356591621 | 96.00 | ~4% fewer retired instructions (cold-path outlining, inlining) |
| riscv64 (QEMU host) `bench` real_time (s) | 20.2733 | 19.6477 | 96.91 | Dominated by emulator overhead; guest-code gain cannot be isolated under QEMU |
| riscv64 (QEMU host) `bench` IPC | 3.43 | 3.41 | 99.42 | Host-side emulator metric; not a guest result |
| riscv64 (QEMU host) `bench` cycles | 27787365347 | 26908386567 | 96.84 | Host-side TCG cycles |
| riscv64 (QEMU host) `bench` instructions | 95394076406 | 91832156056 | 96.27 | Host-side TCG instructions |

Additional finding: the recipe's `-O3` was silently overridden by CMake's `CMAKE_C_FLAGS_RELWITHDEBINFO=-O2`; the corrected builds (`x86-build-opt`, `riscv-build-opt`) end in `-O3 -O3`. Both corrected builds pass 19/19 tests.

### 5.4 Recommended optimizations
| Priority | Optimization | Expected Gain | Effort | Notes |
|:--:|---|:--:|:--:|---|
| 1 | Fix effective optimization level (`-O3` overridden by `-O2`) | Low–Med | Low | Verified in `flags.make`; no correctness risk |
| 2 | Fast number printing (itoa for integers; fast dtoa / drop `sscanf` round-trip) | High | Medium | Targets the #1 x86 cost (`__sprintf_chk` ~20.5% children); native-RISC-V benefit plausibly ≥ x86; must preserve JSON semantics |
| 3 | `cJSON_InitHooks` arena/pool + temp-buffer reuse in `parse_number` | Med–High | High (arena) | Removes per-node `malloc`/`free` (~7,000 allocations/parse) |
| 4 | Allocator replacement (mimalloc → jemalloc → tcmalloc) | Med | Low | Needs a cross-built allocator for riscv; none available in this container |
| 5 | Pre-size print buffer (`cJSON_PrintBuffered`/`cJSON_PrintPreallocated`) | Medium | Low | Eliminates ~9 growing `realloc`+`memcpy` per iteration |
| 6 | LTO (`-flto`) | Low–Med | Low | Single-TU bench sees little; helps multi-TU library builds |
| 7 | PGO (`-fprofile-generate`/`-fprofile-use`) | Med | Medium | Applied and measured: ~5% x86 elapsed; profiles ideally collected on native target hardware |
| 8 | Drop `ENABLE_LOCALES`; `-fno-plt`; `-fno-stack-protector` | Low | Low | Removes per-number `localeconv()` and PLT/GS overhead; stack protector is a security tradeoff |
| 9 | Static or musl libc; newer/vendor RISC-V GCC | Low–Med | High | Smaller/heavier-libc printf could compound gain #2 |
| 10 | `-march` tuning for real hardware (`rv64gc` or `rv64gcv_zba_zbb_zbc_zbs`) | Med on native | Low | **Correctness critical:** `rv64gcv` raises SIGILL on non-V hardware |
| 11 | Manual RVV SIMD for string scans | Low | Very High | Not recommended; data-dependent escapes and toolchain-specific intrinsics |

Unmeasured expected gains are **NOT MEASURED**; only the values in §5.3 were measured.

---

## Improvement of 1_1_1 compared to 1_1_1_pgo

| Measured | Baseline value | Optimized value | Improvement % | Parameter |
|---|---|---|---|---|
| bench | 1.68561 | 1.6009 | 94.97 | real_time |
| bench | 3.33 | 3.38 | 101.5 | IPC |
| bench | 2303532853 | 2179342513 | 94.61 | cycles |
| bench | 7662840791 | 7356591621 | 96 | instructions |

## Improvement of 1_2_2 compared to 1_2_2_pgo

| Measured | Baseline value | Optimized value | Improvement % | Parameter |
|---|---|---|---|---|
| bench | 20.2733 | 19.6477 | 96.91 | real_time |
| bench | 3.43 | 3.41 | 99.42 | IPC |
| bench | 27787365347 | 26908386567 | 96.84 | cycles |
| bench | 95394076406 | 91832156056 | 96.27 | instructions |

> The `1_2_2` measurements are **HOST-SIDE under QEMU emulation** and must not be read as native RISC-V performance.

---

## Cross-table: x86 vs riscv_qemu

### EVENT: BRANCH-MISSES

| Symbol | x86 % | riscv_qemu % | Delta % |
|:------------------------|---------:|---------:|-------:|
| \[unknown\]             |     55.18 |    100.00 |  +44.82 |
| malloc                  |     19.53 |      0.00 |  -19.53 |
| print\_value            |     11.25 |      0.00 |  -11.25 |
| parse\_value            |      9.47 |      0.00 |   -9.47 |
| ensure                  |      1.70 |      0.00 |   -1.70 |
| strncmp@plt             |      0.81 |      0.00 |   -0.81 |
| strlen@plt              |      0.70 |      0.00 |   -0.70 |
| cfree                   |      0.25 |      0.00 |   -0.25 |
| print\_string\_ptr      |      0.20 |      0.00 |   -0.20 |
| parse\_string           |      0.19 |      0.00 |   -0.19 |
| cJSON\_Delete           |      0.17 |      0.00 |   -0.17 |
| strtod@plt              |      0.15 |      0.00 |   -0.15 |
| realloc                 |      0.09 |      0.00 |   -0.09 |
| main                    |      0.08 |      0.00 |   -0.08 |
| \_\_sprintf\_chk@plt    |      0.06 |      0.00 |   -0.06 |
| cJSON\_Parse            |      0.05 |      0.00 |   -0.05 |
| \_\_uflow               |      0.03 |      0.00 |   -0.03 |
| strtod                  |      0.03 |      0.00 |   -0.03 |
| cJSON\_PrintUnformatted |      0.03 |      0.00 |   -0.03 |
| \_\_sprintf\_chk        |      0.03 |      0.00 |   -0.03 |

### EVENT: CACHE-MISSES

| Symbol | x86 % | riscv_qemu % | Delta % |
|:-------------------------|---------:|---------:|-------:|
| \[unknown\]              |     64.58 |    100.00 |  +35.42 |
| print\_string\_ptr       |      9.24 |      0.00 |   -9.24 |
| print\_value             |      5.88 |      0.00 |   -5.88 |
| cfree                    |      4.87 |      0.00 |   -4.87 |
| ensure                   |      3.29 |      0.00 |   -3.29 |
| malloc                   |      2.67 |      0.00 |   -2.67 |
| parse\_value             |      2.55 |      0.00 |   -2.55 |
| cJSON\_Delete            |      2.29 |      0.00 |   -2.29 |
| strlen@plt               |      0.90 |      0.00 |   -0.90 |
| strncmp@plt              |      0.75 |      0.00 |   -0.75 |
| parse\_string            |      0.71 |      0.00 |   -0.71 |
| \_\_sprintf\_chk         |      0.68 |      0.00 |   -0.68 |
| memcpy@plt               |      0.66 |      0.00 |   -0.66 |
| strchrnul@plt            |      0.23 |      0.00 |   -0.23 |
| cJSON\_PrintUnformatted  |      0.15 |      0.00 |   -0.15 |
| \_\_libc\_alloca\_cutoff |      0.11 |      0.00 |   -0.11 |
| \_IO\_str\_underflow     |      0.11 |      0.00 |   -0.11 |
| \_\_isoc99\_sscanf       |      0.09 |      0.00 |   -0.09 |
| strtod                   |      0.07 |      0.00 |   -0.07 |
| realloc                  |      0.06 |      0.00 |   -0.06 |

### EVENT: CYCLES

| Symbol | x86 % | riscv_qemu % | Delta % |
|:---------------------|---------:|---------:|-------:|
| \[unknown\]          |     63.17 |    100.00 |  +36.83 |
| print\_value         |      6.86 |      0.00 |   -6.86 |
| parse\_value         |      6.73 |      0.00 |   -6.73 |
| malloc               |      5.40 |      0.00 |   -5.40 |
| print\_string\_ptr   |      3.48 |      0.00 |   -3.48 |
| parse\_string        |      3.15 |      0.00 |   -3.15 |
| cfree                |      3.15 |      0.00 |   -3.15 |
| ensure               |      2.81 |      0.00 |   -2.81 |
| cJSON\_Delete        |      1.86 |      0.00 |   -1.86 |
| strlen@plt           |      0.61 |      0.00 |   -0.61 |
| strncmp@plt          |      0.59 |      0.00 |   -0.59 |
| \_\_isoc99\_sscanf   |      0.41 |      0.00 |   -0.41 |
| \_\_sprintf\_chk     |      0.31 |      0.00 |   -0.31 |
| strchrnul@plt        |      0.26 |      0.00 |   -0.26 |
| memcpy@plt           |      0.25 |      0.00 |   -0.25 |
| strtod@plt           |      0.16 |      0.00 |   -0.16 |
| \_\_uflow            |      0.14 |      0.00 |   -0.14 |
| \_IO\_default\_uflow |      0.14 |      0.00 |   -0.14 |
| \_IO\_setb           |      0.11 |      0.00 |   -0.11 |
| \_IO\_str\_underflow |      0.11 |      0.00 |   -0.11 |

> The `riscv_qemu` column is host-side under QEMU; 100% `[unknown]` reflects unresolved emulator JIT symbols, not a software hotspot.

## Cross-table: x86_cjson_test vs riscv_qemu_cjson_test

### EVENT: BRANCH-MISSES

| Symbol | x86_cjson_test % | riscv_qemu_cjson_test % | Delta % |
|:---------------|---------:|---------:|-------:|
| \[unknown\] (/ |      0.00 |     96.57 |  +96.57 |
| \[unknown\]    |      0.00 |      3.43 |   +3.43 |

### EVENT: CACHE-MISSES

| Symbol | x86_cjson_test % | riscv_qemu_cjson_test % | Delta % |
|:---------------|---------:|---------:|-------:|
| \[unknown\]    |    100.00 |     71.01 |  -28.99 |
| \[unknown\] (/ |      0.00 |     28.99 |  +28.99 |

### EVENT: CYCLES

| Symbol | x86_cjson_test % | riscv_qemu_cjson_test % | Delta % |
|:---------------|---------:|---------:|-------:|
| \[unknown\] (/ |     33.89 |     91.19 |  +57.30 |
| \[unknown\]    |     65.78 |      8.81 |  -56.97 |
| ensure         |      0.33 |      0.00 |   -0.33 |

## Cross-table: x86_opt vs riscv_qemu_opt

### EVENT: BRANCH-MISSES

| Symbol | x86_opt % | riscv_qemu_opt % | Delta % |
|:---------------------------|---------:|---------:|-------:|
| \[unknown\]                |      1.37 |     91.92 |  +90.55 |
| \[unknown\] (/             |     78.67 |      8.08 |  -70.59 |
| print\_value               |      8.39 |      0.00 |   -8.39 |
| parse\_value.cold          |      6.09 |      0.00 |   -6.09 |
| parse\_value               |      3.78 |      0.00 |   -3.78 |
| ensure                     |      0.95 |      0.00 |   -0.95 |
| print\_string\_ptr         |      0.25 |      0.00 |   -0.25 |
| cJSON\_Delete              |      0.25 |      0.00 |   -0.25 |
| main                       |      0.13 |      0.00 |   -0.13 |
| cJSON\_ParseWithLengthOpts |      0.06 |      0.00 |   -0.06 |
| print.constprop.0          |      0.06 |      0.00 |   -0.06 |

### EVENT: CACHE-MISSES

| Symbol | x86_opt % | riscv_qemu_opt % | Delta % |
|:------------------------|---------:|---------:|-------:|
| \[unknown\]             |     18.62 |     65.12 |  +46.50 |
| \[unknown\] (/          |     63.79 |     34.88 |  -28.91 |
| print\_value            |      5.92 |      0.00 |   -5.92 |
| print\_string\_ptr      |      5.66 |      0.00 |   -5.66 |
| cJSON\_Delete           |      2.79 |      0.00 |   -2.79 |
| parse\_value            |      2.07 |      0.00 |   -2.07 |
| ensure                  |      0.61 |      0.00 |   -0.61 |
| print\_string\_ptr.cold |      0.52 |      0.00 |   -0.52 |
| parse\_value.cold       |      0.01 |      0.00 |   -0.01 |

### EVENT: CYCLES

| Symbol | x86_opt % | riscv_qemu_opt % | Delta % |
|:------------------------|---------:|---------:|-------:|
| \[unknown\]             |      3.75 |     35.26 |  +31.51 |
| \[unknown\] (/          |     75.33 |     64.74 |  -10.59 |
| print\_value            |      7.83 |      0.00 |   -7.83 |
| parse\_value            |      6.83 |      0.00 |   -6.83 |
| print\_string\_ptr      |      2.57 |      0.00 |   -2.57 |
| cJSON\_Delete           |      1.26 |      0.00 |   -1.26 |
| parse\_value.cold       |      1.19 |      0.00 |   -1.19 |
| ensure                  |      1.06 |      0.00 |   -1.06 |
| print\_string\_ptr.cold |      0.19 |      0.00 |   -0.19 |

> In the optimized x86 record the libc DSO is reported as `(deleted)`, so its frames appear as `[unknown] (/ (deleted))` (offset-identical to baseline libc frames) — a symbolization artifact, not a performance change.

---

## Saved profile data (`cJSON.json`)

```json
{
  "1_1_1": {
    "cJSON_test": {
      "build_name": "1_1_1",
      "executable": "cJSON_test",
      "executable_run_success": false,
      "real_time": null,
      "user_time": null,
      "kernel_time": null,
      "perf_stat": null,
      "perf_record_name": null,
      "perf_script_name": null,
      "perf_archive_name": null
    }
  }
}
```

> `executable_run_success` is `false` because `amixis run/profile` could not instantiate the build (`Invalid local machine arch: riscv, your machine is x86_64`); the entry is incomplete tool output, not a measured cJSON failure. All performance data in this report comes from the manual `perf` fallback.

---

## 6. Notes About Exploration Process

1. **amixis 0.2.0 cannot handle the address-less riscv platform.** `amixis build` and `amixis profile` fail for **both** builds with `Invalid local machine arch: riscv, your machine is x86_64`, because the configurator eagerly instantiates every platform and treats address-less platform 2 as the local x86_64 host. Manual CMake/perf fallbacks were used throughout. `amixis validate` and `amixis compare` work.
2. **Invalid provided flag:** `-march=rv64gcvb` was rejected by GCC 13 ("ISA string is not in canonical order" / no `b` shorthand); corrected to `-march=rv64gcv` (valid equivalents for bitmanip: `rv64gcv_zba_zbb_zbc_zbs`).
3. **CMake test option name:** `-DBUILD_TESTING=ON` is a no-op for cJSON (real option `ENABLE_CJSON_TEST`, ON by default).
4. **CMake emulator not wired:** `CMAKE_CROSSCOMPILING_EMULATOR` is ignored because host/target `CMAKE_SYSTEM_NAME` are both Linux; `ctest` on riscv fails 19/19 with `Could not open '/lib/ld-linux-riscv64-lp64d.so.1'`. All 19 binaries pass when run explicitly under `qemu-riscv64-static -L /usr/riscv64-linux-gnu`.
5. **`file` command absent** on the host; ELF arch confirmed with `readelf -h` (x86-64 vs RISC-V ELF64).
6. **`nice -n -20` and `chrt` denied** (container lacks CAP_SYS_NICE); all measurements at nice 0.
7. **CPU governor fixed at `powersave`** (sysfs read-only), effective ~1.3 GHz. Absolute times are on a throttled CPU; relative comparison is valid because both platforms were measured identically.
8. **`amphimixis-analyze-vectorization` failed for riscv (exit 1)**; `riscv64-linux-gnu-objdump` fallback used.
9. **Kernel/libc symbol resolution restricted:** stripped libc and `kptr_restrict` make many samples `[unknown]`; the optimized x86 record additionally classifies libc as `(deleted)`.
10. **PGO build correction:** the literal one-shot PGO commands produce a profile-name mismatch (silent no-op); object-file PGO with stable profile names was used so PGO genuinely applied (0 missing-profile warnings).

### QEMU / emulation caveats (repeated)
- riscv64 was executed under `qemu-riscv64-static` 8.2.2 (single-threaded TCG); **all riscv timing includes emulation overhead (~12× the native x86 wall time) and does not reflect native RISC-V hardware performance.**
- perf on the riscv runs samples the emulator host process; counters are host-side and guest instruction-level counters are unobtainable. RISC-V hotspots are **NOT AVAILABLE**; the riscv cross-table `[unknown]` entries are unresolved emulator JIT symbols.
- No native RISC-V hardware measurement was possible in this container.

---

## 7. Migration Readiness Summary

| Check | Status |
|---|---|
| Builds on reference (x86_64) | ✅ SUCCESS (manual CMake fallback; `amixis build` tool failed) |
| Tests pass on reference | ✅ 19/19 CTest, 0 failed (153 Unity assertions, 1 ignored) |
| Builds on target (riscv64) | ✅ SUCCESS (manual cross CMake; amixis tool failed) |
| Tests pass on target | ✅ 19/19 under QEMU user-mode emulation |
| Zero external dependencies | ✅ None (libc + libm only) |
| No hand-written intrinsics | ✅ 0 SIMD intrinsics / 0 inline asm in source |
| Alignment safe | ✅ No punning, no unaligned access, endian-neutral |
| Exceptions handled | ✅ N/A — ANSI C89, no exceptions |
| Auto-vectorization | ⚠️ None fires: 0 RVV instructions emitted even with `-march=rv64gcv` (scalar, branchy hot loops) |

**Migration Verdict: MINOR CONCERNS** — the source is architecture-agnostic and migrates cleanly (builds and all tests pass on riscv64, zero dependencies, no intrinsics, no alignment/exception issues). The concerns are environmental/deployment rather than source portability: no native RISC-V hardware profiling was possible (QEMU host-side only), and the chosen `-march` must match real target hardware.

### Required Actions
1. **Verify the target ISA before shipping.** `-march=rv64gcv` will raise SIGILL on hardware without the V extension; use `-march=rv64gc` (or `rv64gcv_zba_zbb_zbc_zbs`) if V is not guaranteed.
2. **Profile on native RISC-V hardware** to replace the QEMU host-side measurements; guest counters and true hotspots are currently NOT AVAILABLE.
3. **Fix the effective optimization level** in the build (`-O3` is overridden by CMake's `-O2` for `RelWithDebInfo`).
4. **Consider a fast number-printing path and allocation reduction** (`sprintf`/`sscanf` and per-node `malloc` dominate the x86 profile; native RISC-V is expected to be at least as formatting-bound).
5. **Report/fix the `__GNUCC__` typo** in `cJSON_Utils.c` (should be `__GNUC__`), which disables GCC visibility pragmas for that translation unit.
6. **Enable `ENABLE_CJSON_UTILS=ON`** if the Utils/patch tests are required in the migration test matrix.
