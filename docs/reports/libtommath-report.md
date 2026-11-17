# libtommath — Migration Readiness Report

**Project:** libtommath
**Reference platform:** x86_64 (native)
**Target platform:** riscv64, executed under **qemu-user** (`qemu-riscv64-static` via binfmt_misc)
**Analysis date:** 2026-10-04
**Workspace:** `/work/libtommath-workspace/`

---

## 1. Repository & Project Status

| Field | Value |
|---|---|
| Repository URL | https://github.com/libtom/libtommath.git |
| Latest commit | `ae40a87a920099a7d9d00979570e0c8d917a1fd7` (2026-04-20) |
| Total commits | 1568 |
| Latest stable tag | `v1.3.0` (2024-03-27); latest overall `v1.3.1-rc1` (release candidate) |
| `git describe` | `v1.3.0-418-gae40a87` |
| Default branch | `develop` |
| Activity | Sporadically maintained (4 commits in last year; mature/stable; not archived) |
| Build systems | CMake, Make (`makefile.shared`, `makefile.unix`, `makefile.mingw`, `makefile.msvc`), `Package.swift`, Visual Studio solution |
| Test suite | CTest target `test-ltm` → `demo/test.c` with **50 tests**; plus `mtest` differential tester |
| CI | GitHub Actions (x86-64 GCC/Clang, 32-bit, sanitizers, valgrind, LTO, c89/c99); Ubuntu-24.04-arm (aarch64). **No riscv CI job.** |
| External dependencies | **None** (self-contained C library; libc + compiler builtins only) |
| Distro packages | Debian `libtommath 1.3.0-1`; Alpine `libtommath 1.3.0-r1` (riscv64); openSUSE `Factory:RISCV`; Yocto `meta-oe` recipe |
| Forks with riscv64 patches | **None found** (GitHub search `libtommath riscv` = 0; no riscv branches/commits upstream) |

---

## 2. Platform-Specific Code Analysis

### 2.1 Architecture / capability macros

| Macro(s) | File:Line | What it guards | Target-arch impact |
|---|---|---|---|
| `_MSC_VER`, `__LLP64__`, `__e2k__`, `__LCC__` | `tommath.h:20` | Force `MP_32BIT` | none (not defined by riscv64 GCC) |
| `__x86_64__`, `_M_X64`, `__powerpc64__`, `__aarch64__`, `__s390x__`, `__sparcv9`, `__ia64`, `__LP64__`, `_LP64`, `__64BIT__` … | `tommath.h:25-30` | Select 64-bit limb mode | `__riscv` absent, but riscv64 GCC defines `__LP64__`/`_LP64` → 64-bit selected correctly |
| `__GNUC__` + `__SIZEOF_INT128__` + `!__hppa` | `tommath.h:32` | Enable `MP_64BIT` (`unsigned __int128`) | RISC-V GCC defines `__SIZEOF_INT128__` → enabled |
| `__GNUC__ >= 4` | `tommath.h:130,147,153,162` | `sentinel`/`warn_unused_result`/`deprecated` attrs | applies |
| `__GNUC__>=4 && !_WIN32 && !__CYGWIN__` | `tommath_private.h:19` | `visibility("hidden")` | applies |
| `__STDC_IEC_559__`, `__GCC_IEC_559`, `__x86_64__`, `__i386__`, `__aarch64__`, `__arm__` … | `tommath_private.h:178-181` | Define `MP_HAS_SET_DOUBLE` | `__riscv` absent, but `rv64gc` (hard-float) defines `__GCC_IEC_559` → enabled; a soft-float ABI (`-mabi=lp64`, no F/D) would disable it |
| `__GNUC__` | `tommath_private.h:239` | `__thread` TLS; `#error` otherwise | applies |
| `__WORDSIZE == 64` | `tommath_c89.h:29,36` | C89 compatibility header pointer/printf width | glibc-specific; affects optional `make c89` mode only |
| `_MSC_VER` | `demo/test.c:660,693`, `mp_set_double.c:41` | MSVC pragmas | not applicable |

### 2.2 Platform preprocessor guards (OS / runtime)

| Guard | File:Line | Platform | Scope |
|---|---|---|---|
| `__FreeBSD__`/`__OpenBSD__`/`__NetBSD__`/`__DragonFly__` | `s_mp_rand_platform.c:10` | BSD | `arc4random_buf` CSPRNG |
| `_WIN32`/`_WIN32_WINNT`/`LTM_WIN32_BCRYPT` | `s_mp_rand_platform.c:19,22,32`; `demo/test.c:2463,2470` | Windows | `BCryptGenRandom` / thread shims |
| `__linux__ && __GLIBC_PREREQ(2,25)` | `s_mp_rand_platform.c:62-63` | Linux/glibc | `getrandom()` (used on riscv64 glibc ≥ 2.25) |
| `!S_READ_WINCSP_C && !MP_NO_DEV_URANDOM` | `s_mp_rand_platform.c:90` | POSIX | `/dev/urandom` fallback |
| `MULTI_THREADED_PTHREAD` / `_MSVC` | `demo/test.c:2488` | POSIX/Windows | test-runner threads |

### 2.3 Inline assembly / intrinsics

- **No vector intrinsics anywhere in the library source** (no SSE/AVX, NEON, or RVV).
- Endianness is handled at runtime (`MP_GET_ENDIANNESS()`), not via compile-time macros.
- **One blocker (optional, not built by CMake):** `demo/timing.c:59-92` `TIMFUNC()` supports x86 `rdtsc` and IA64 `mov %0=ar.itc`, with `#error need rdtsc function for this build` otherwise. On riscv64 GCC it falls into the IA64 `#else` branch and **fails to compile**. This affects only the optional legacy `make timing` benchmark, not the library or the CMake/CTest suite.

### 2.4 Portability verdict

| Aspect | Verdict |
|---|---|
| No exceptions | **N/A** — pure C library; no C++ exception handling required |
| Alignment safe | **YES** — no compile-time endianness/alignment assumptions; endianness detected at runtime |
| Embedded usability | **GOOD** — no external dependencies; static-link friendly; ~11k LOC |
| Overall portability | **LOW RISK** — buildable and packageable on riscv64 (Alpine/openSUSE/Debian/Yocto); only optional `demo/timing.c` benchmark is non-portable |

---

## 3. Build & Test Results

| Build | Platform | Toolchain | Effective opt | Build | Tests (passed/total) | Notes |
|---|---|---|---|---|---|---|
| `1_1_1` baseline | x86_64 native | gcc 13.3.0 | `-O2` (RelWithDebInfo overrides `-O3`) | PASSED | 50/50 (CTest 1/1) | dynamic PIE, `-march=native` |
| `1_2_2` baseline | riscv64 under qemu-user | riscv64-linux-gnu-gcc 13.3.0 | `-O2` | PASSED | 50/50 (CTest 1/1, 40.84 s) | static RISC-V ELF, `-march=rv64gc` |
| `1_1_3` optimized | x86_64 native | gcc 13.3.0 | **`-O3`** | PASSED | 50/50 (CTest 1/1) | dynamic PIE, `-march=native`, `CMAKE_BUILD_TYPE=None` |
| `1_2_4` optimized | riscv64 under qemu-user | riscv64-linux-gnu-gcc 13.3.0 | **`-O3`** | PASSED | 50/50 (CTest 1/1, 41.01 s) | static RISC-V ELF, `-march=rv64gc` |

**Build/test failures:** none. Internal suite reports `Tests OK/NOP/FAIL: 50/0/0` on all four builds. Target tests were run both directly via `qemu-riscv64-static <binary>` and through kernel binfmt routing.

**Warnings:** CMake reports `CMAKE_CXX_FLAGS` unused (project is C-only) — harmless. `perf_event_paranoid` write fails (read-only `/proc/sys/kernel`, but already `-1`).

---

## 4. Performance Comparison

### 4.1 Experimental conditions

| Condition | Reference (x86_64) | Target (riscv64 / qemu-user) |
|---|---|---|
| CPU | AMD Ryzen 5 7640HS, 6C/12T, L1d 192K, L2 6M, L3 16M | same physical host |
| Execution | native | `qemu-riscv64-static` 8.2.2 user-mode (binfmt_misc) |
| Pinning | `taskset -c 0` | `taskset -c 0` (host CPU 0) |
| Priority | `nice -n -20` attempted — FAILED (EPERM); ran at nice 0 | same, failed → nice 0 |
| Warmup | 2 runs | 2 runs |
| Measurement runs | 8 | 8 |
| Frequency check | `/sys/.../scaling_cur_freq` sampled before/after; governor `powersave`, boost varies | same |
| perf counter events | `perf stat -ddd` + `perf record` | `perf stat -ddd` + `perf record` |

### 4.2 qemu-user / emulation caveat (CRITICAL)

The riscv64 target binary does **not** run on RISC-V hardware. It is a statically-linked RISC-V ELF executed through the host kernel's `binfmt_misc` → `qemu-riscv64-static` emulator on the x86_64 host. Therefore:
- **All target `perf stat` counters measure the HOST `qemu-riscv64-static` process, not guest RISC-V instructions.**
- **Only wall-clock elapsed time is meaningful for the target.**
- Target hotspot attribution is impossible (100% `[unknown]` / host-qemu + TCG JIT).
- Target wall-clock includes full dynamic-binary-translation overhead and does **not** reflect native RISC-V performance.

### 4.3 Key metrics (`demo/test-ltm`)

| Metric | `1_1_1` x86 baseline | `1_2_2` riscv baseline (qemu) | `1_1_3` x86 optimized | `1_2_4` riscv optimized (qemu) | Validity |
|---|---|---|---|---|---|
| Elapsed time (single run, libtommath.json) | 3.84 s | 42.69 s | 3.99 s | 39.98 s | target = emulated |
| Elapsed time (8-run mean, improvements.json) | 3.897 s | 40.017 s | 3.933 s | 39.374 s | target = emulated |
| IPC | 4.32 | 4.79 | 4.14 | 4.67 | target = HOST-QEMU |
| L1-dcache miss rate | 0.03% | 0.15% | 0.03% | 0.29% | target = HOST-QEMU |
| LLC miss rate | `<not supported>` | `<not supported>` | `<not supported>` | `<not supported>` | NOT AVAILABLE |
| Branch misprediction rate | 0.19% | 0.08% | 0.19% | 0.08% | target = HOST-QEMU |
| Frontend Bound | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | PMU lacks topdown-slot events |
| Backend Bound | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | PMU lacks topdown-slot events |
| Retiring | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | PMU lacks topdown-slot events |
| stalled-cycles-frontend (proxy) | 5.45% | 5.42% | 5.66% | 5.41% | target = HOST-QEMU |

### 4.4 Hotspots

**Reference x86_64 (baseline `1_1_1`, from cross-table CYCLES):** `s_mp_mul_comba` 12.97%, `s_mp_sqr_comba` 8.88%, `mp_clamp` 8.65%, `mp_mul` 6.58%, `s_mp_sub` 4.39%, `s_mp_montgomery_reduce_comba` 4.01%, `mp_cmp_mag` 3.48%, `mp_mul_d` 3.30%. Workload is scalar carry-propagating bignum arithmetic; no SIMD in the hot path.

**Reference x86_64 (optimized `1_1_3`, from cross-table CYCLES):** `s_mp_sqr_comba` 14.03%, `mp_clamp` 12.34%, `s_mp_mul_comba` 9.78%, `s_mp_sub` 4.20%, `mp_mul_d` 3.65%, `mp_grow` 3.48%, `mp_cmp_mag` 3.04%, `s_mp_montgomery_reduce_comba` 2.55%.

**Target riscv64 (both builds):** guest hotspot data **NOT AVAILABLE** — under qemu-user 100% of samples resolve to the host emulator (see cross-tables: target column is entirely `[unknown]`). Host-side execution is dominated by `qemu-riscv64-static` and its TCG translation buffer.

### 4.5 Bottleneck summary

1. **QEMU user-mode dynamic binary translation — decisive.** The target is far slower in wall-clock than the reference; all target counters and samples belong to the host emulator. This cost cannot be removed by any project change and is not representative of native RISC-V.
2. **Scalar carry-bound bignum kernels (both).** Comba multiply/square, Montgomery reduction and `mp_clamp` dominate the reference profile. They are inherently serial and not auto-vectorizable.
3. **Static vs dynamic linkage (target).** The target must be statically linked for qemu-user, inflating the binary (absorbs libc) and RSS; this is a linkage artifact, not ISA code bloat.

### 4.6 Vectorization intrinsics

No hand-written SIMD intrinsics exist in the source. x86 auto-vectorization in the binary is confined to floating-point test-harness code; the target rv64gc ISA has no V extension, and GCC emitted none. Porting is therefore not required.

### 4.7 Cross-table — baseline builds

## Cross-table of 1_1_1 vs 1_2_2

# Cross-tables for 1\_\_1\_\_1..demo\_stest-ltm and 1\_\_2\_\_2..demo\_stest-ltm

## EVENT: CYCLES

| Symbol                           | profiling-artifacts/1_1_1 % | profiling-artifacts/1_2_2 % | Delta % |
|:---------------------------------|---------------------------:|---------------------------:|-------:|
| \[unknown\]                      |                       21.65 |                      100.00 |  +78.35 |
| s\_mp\_mul\_comba                |                       12.97 |                        0.00 |  -12.97 |
| s\_mp\_sqr\_comba                |                        8.88 |                        0.00 |   -8.88 |
| mp\_clamp                        |                        8.65 |                        0.00 |   -8.65 |
| mp\_mul                          |                        6.58 |                        0.00 |   -6.58 |
| s\_mp\_sub                       |                        4.39 |                        0.00 |   -4.39 |
| s\_mp\_montgomery\_reduce\_comba |                        4.01 |                        0.00 |   -4.01 |
| mp\_cmp\_mag                     |                        3.48 |                        0.00 |   -3.48 |
| mp\_mul\_d                       |                        3.30 |                        0.00 |   -3.30 |
| mp\_grow                         |                        2.31 |                        0.00 |   -2.31 |
| s\_mp\_div\_school               |                        2.31 |                        0.00 |   -2.31 |
| s\_mp\_sqr                       |                        2.14 |                        0.00 |   -2.14 |
| mp\_lshd                         |                        1.88 |                        0.00 |   -1.88 |
| \_\_libc\_calloc                 |                        1.26 |                        0.00 |   -1.26 |
| realloc                          |                        1.17 |                        0.00 |   -1.17 |
| mp\_div\_2d                      |                        1.02 |                        0.00 |   -1.02 |
| s\_mp\_zero\_digs                |                        0.95 |                        0.00 |   -0.95 |
| cfree                            |                        0.92 |                        0.00 |   -0.92 |
| mp\_mul\_2d                      |                        0.84 |                        0.00 |   -0.84 |
| s\_mp\_add                       |                        0.77 |                        0.00 |   -0.77 |

## EVENT: CACHE-MISSES

| Symbol                              | profiling-artifacts/1_1_1 % | profiling-artifacts/1_2_2 % | Delta % |
|:------------------------------------|---------------------------:|---------------------------:|-------:|
| \[unknown\]                         |                       90.32 |                      100.00 |   +9.68 |
| s\_mp\_sqr\_comba                   |                        1.15 |                        0.00 |   -1.15 |
| mp\_div\_2d                         |                        0.87 |                        0.00 |   -0.87 |
| mp\_prime\_strong\_lucas\_selfridge |                        0.83 |                        0.00 |   -0.83 |
| mp\_lshd                            |                        0.81 |                        0.00 |   -0.81 |
| s\_mp\_sub                          |                        0.78 |                        0.00 |   -0.78 |
| s\_mp\_mul\_comba                   |                        0.64 |                        0.00 |   -0.64 |
| mp\_mul                             |                        0.52 |                        0.00 |   -0.52 |
| test\_s\_mp\_mul\_balance           |                        0.33 |                        0.00 |   -0.33 |
| mp\_clamp                           |                        0.29 |                        0.00 |   -0.29 |
| mp\_reduce\_is\_2k                  |                        0.27 |                        0.00 |   -0.27 |
| mp\_mul\_d                          |                        0.25 |                        0.00 |   -0.25 |
| mp\_init                            |                        0.24 |                        0.00 |   -0.24 |
| mp\_expt\_n                         |                        0.24 |                        0.00 |   -0.24 |
| mp\_exch                            |                        0.24 |                        0.00 |   -0.24 |
| mp\_exptmod                         |                        0.22 |                        0.00 |   -0.22 |
| mp\_clear                           |                        0.21 |                        0.00 |   -0.21 |
| cfree                               |                        0.18 |                        0.00 |   -0.18 |
| s\_mp\_exptmod\_fast                |                        0.16 |                        0.00 |   -0.16 |
| mp\_grow                            |                        0.11 |                        0.00 |   -0.11 |

## EVENT: BRANCH-MISSES

| Symbol                                  | profiling-artifacts/1_1_1 % | profiling-artifacts/1_2_2 % | Delta % |
|:----------------------------------------|---------------------------:|---------------------------:|-------:|
| \[unknown\]                             |                       23.10 |                      100.00 |  +76.90 |
| s\_mp\_sub                              |                       10.40 |                        0.00 |  -10.40 |
| s\_mp\_div\_school                      |                        6.75 |                        0.00 |   -6.75 |
| mp\_cmp\_mag                            |                        6.71 |                        0.00 |   -6.71 |
| mp\_mul\_d                              |                        6.39 |                        0.00 |   -6.39 |
| s\_mp\_sqr\_comba                       |                        4.72 |                        0.00 |   -4.72 |
| s\_mp\_mul\_comba                       |                        4.62 |                        0.00 |   -4.62 |
| mp\_clamp                               |                        4.12 |                        0.00 |   -4.12 |
| s\_mp\_montgomery\_reduce\_comba        |                        3.59 |                        0.00 |   -3.59 |
| mp\_exch                                |                        3.32 |                        0.00 |   -3.32 |
| mp\_grow                                |                        2.30 |                        0.00 |   -2.30 |
| s\_mp\_sqr                              |                        2.25 |                        0.00 |   -2.25 |
| \_\_libc\_calloc                        |                        1.85 |                        0.00 |   -1.85 |
| s\_mp\_fp\_log\_fraction\_d.constprop.0 |                        1.58 |                        0.00 |   -1.58 |
| mp\_lshd                                |                        1.53 |                        0.00 |   -1.53 |
| s\_mp\_div\_3                           |                        1.22 |                        0.00 |   -1.22 |
| mp\_mul                                 |                        1.22 |                        0.00 |   -1.22 |
| s\_mp\_add                              |                        1.19 |                        0.00 |   -1.19 |
| mp\_clear                               |                        0.92 |                        0.00 |   -0.92 |
| mp\_sub                                 |                        0.92 |                        0.00 |   -0.92 |

### 4.8 Cross-table — optimized builds

## Cross-table of 1_1_3 vs 1_2_4

# Cross-tables for 1\_\_1\_\_3..demo\_stest-ltm and 1\_\_2\_\_4..demo\_stest-ltm

## EVENT: CYCLES

| Symbol                           | /work/1_1_3 % | /work/1_2_4 % | Delta % |
|:---------------------------------|-------------:|-------------:|-------:|
| \[unknown\] (/                   |         24.07 |         66.35 |  +42.28 |
| \[unknown\]                      |          0.20 |         33.65 |  +33.45 |
| s\_mp\_sqr\_comba                |         14.03 |          0.00 |  -14.03 |
| mp\_clamp                        |         12.34 |          0.00 |  -12.34 |
| s\_mp\_mul\_comba                |          9.78 |          0.00 |   -9.78 |
| s\_mp\_sub                       |          4.20 |          0.00 |   -4.20 |
| mp\_mul\_d                       |          3.65 |          0.00 |   -3.65 |
| mp\_grow                         |          3.48 |          0.00 |   -3.48 |
| mp\_cmp\_mag                     |          3.04 |          0.00 |   -3.04 |
| s\_mp\_montgomery\_reduce\_comba |          2.55 |          0.00 |   -2.55 |
| s\_mp\_sqr                       |          2.22 |          0.00 |   -2.22 |
| mp\_lshd                         |          2.00 |          0.00 |   -2.00 |
| mp\_div\_2d                      |          1.84 |          0.00 |   -1.84 |
| mp\_mul                          |          1.73 |          0.00 |   -1.73 |
| s\_mp\_div\_school               |          1.67 |          0.00 |   -1.67 |
| s\_mp\_add                       |          1.30 |          0.00 |   -1.30 |
| \_\_udivti3                      |          1.23 |          0.00 |   -1.23 |
| s\_mp\_zero\_digs                |          0.95 |          0.00 |   -0.95 |
| mp\_mul\_2d                      |          0.70 |          0.00 |   -0.70 |
| mp\_mod\_2d                      |          0.67 |          0.00 |   -0.67 |

## EVENT: CACHE-MISSES

| Symbol               | /work/1_1_3 % | /work/1_2_4 % | Delta % |
|:---------------------|-------------:|-------------:|-------:|
| \[unknown\] (/       |          9.34 |         46.02 |  +36.68 |
| \[unknown\]          |         76.67 |         53.98 |  -22.68 |
| s\_mp\_div\_school   |          3.23 |          0.00 |   -3.23 |
| s\_mp\_mul\_comba    |          2.51 |          0.00 |   -2.51 |
| mp\_cmp\_mag         |          1.45 |          0.00 |   -1.45 |
| mp\_grow             |          1.28 |          0.00 |   -1.28 |
| mp\_lshd             |          0.82 |          0.00 |   -0.82 |
| mp\_prime\_is\_prime |          0.81 |          0.00 |   -0.81 |
| mp\_add\_d           |          0.77 |          0.00 |   -0.77 |
| mp\_clamp            |          0.49 |          0.00 |   -0.49 |
| mp\_rand             |          0.48 |          0.00 |   -0.48 |
| s\_mp\_sqr\_comba    |          0.37 |          0.00 |   -0.37 |
| s\_mp\_copy\_digs    |          0.36 |          0.00 |   -0.36 |
| mp\_mul\_d           |          0.22 |          0.00 |   -0.22 |
| mp\_mul\_2d          |          0.21 |          0.00 |   -0.21 |
| mp\_div\_2d          |          0.20 |          0.00 |   -0.20 |
| mp\_init\_multi      |          0.09 |          0.00 |   -0.09 |
| s\_mp\_sqr           |          0.07 |          0.00 |   -0.07 |
| mp\_exch             |          0.07 |          0.00 |   -0.07 |
| mp\_clear            |          0.07 |          0.00 |   -0.07 |

## EVENT: BRANCH-MISSES

| Symbol                           | /work/1_1_3 % | /work/1_2_4 % | Delta % |
|:---------------------------------|-------------:|-------------:|-------:|
| \[unknown\] (/                   |         18.13 |         61.46 |  +43.33 |
| \[unknown\]                      |          3.82 |         38.54 |  +34.72 |
| mp\_mul\_d                       |          9.71 |          0.00 |   -9.71 |
| s\_mp\_mul\_comba                |          7.67 |          0.00 |   -7.67 |
| s\_mp\_sub                       |          7.34 |          0.00 |   -7.34 |
| s\_mp\_sqr\_comba                |          7.07 |          0.00 |   -7.07 |
| mp\_clamp                        |          6.47 |          0.00 |   -6.47 |
| mp\_cmp\_mag                     |          6.11 |          0.00 |   -6.11 |
| mp\_exch                         |          4.18 |          0.00 |   -4.18 |
| s\_mp\_div\_school               |          3.86 |          0.00 |   -3.86 |
| s\_mp\_add                       |          3.56 |          0.00 |   -3.56 |
| mp\_grow                         |          3.21 |          0.00 |   -3.21 |
| s\_mp\_fp\_log\_d                |          2.71 |          0.00 |   -2.71 |
| s\_mp\_sqr                       |          1.97 |          0.00 |   -1.97 |
| s\_mp\_montgomery\_reduce\_comba |          1.96 |          0.00 |   -1.96 |
| mp\_lshd                         |          1.54 |          0.00 |   -1.54 |
| mp\_copy                         |          1.02 |          0.00 |   -1.02 |
| mp\_sub                          |          0.95 |          0.00 |   -0.95 |
| mp\_mul\_2d                      |          0.92 |          0.00 |   -0.92 |
| s\_mp\_zero\_digs                |          0.80 |          0.00 |   -0.80 |

---

## 5. Optimization Results

### 5.1 Vector instructions in binary

| Binary | Vector instructions | ISAs found |
|---|---|---|
| `1_1_1` / `1_1_3` x86-64 | present (x86 auto-vectorized test-harness code) | VEX/SSE scalar & packed (`vpinsrq`, `vxorpd`, `vxorps`, `vfmadd*`) |
| `1_2_2` / `1_2_4` riscv64 | **0** | none — `.riscv.attributes` = `rv64gc` **without V extension** |

### 5.2 Optimization attempts

| Before | After | Delta | Causal analysis |
|---|---|---|---|
| Effective `-O2` (RelWithDebInfo appended `-g3 -O2`) | Effective `-O3` (`CMAKE_BUILD_TYPE=None`, `-g3` in flags) | see improvements table | `RelWithDebInfo` appends `-g3 -O2` after the recipe's `-O3`; GCC's last `-O` wins, so the original builds ran at `-O2`. Removing the build type lets `-O3` take effect. On the emulated target this reduces the host-QEMU instruction count (the guest dynamic instruction count is lower), yielding a small wall-clock gain; on x86 the change is within run-to-run variance. It cannot close the ~10× emulation gap. |

### 5.3 Improvement of 1_1_1 compared to 1_1_3

| Measured | Baseline value | Optimized value | Improvement % | Parameter | Baseline build | Optimized build |
|---|---|---|---|---|---|---|
| demo/test-ltm | 3.897 | 3.933 | 100.92 | real_time | 1_1_1 | 1_1_3 |
| demo/test-ltm | 3.897 | 3.933 | 100.92 | real_time | 1_1_1 | 1_1_3 |

### 5.4 Improvement of 1_2_2 compared to 1_2_4

| Measured | Baseline value | Optimized value | Improvement % | Parameter | Baseline build | Optimized build |
|---|---|---|---|---|---|---|
| demo/test-ltm | 40.017 | 39.374 | 98.39 | real_time | 1_2_2 | 1_2_4 |
| demo/test-ltm | 40.017 | 39.374 | 98.39 | real_time | 1_2_2 | 1_2_4 |

### 5.5 Recommended optimizations

| Priority | Optimization | Expected gain | Effort | Notes |
|---|---|---|---|---|
| 1 | Force effective `-O3` (applied in `1_1_3` / `1_2_4`) | small (target guest-instruction reduction; ~neutral on x86) | Low | Addresses the RelWithDebInfo flag-ordering defect |
| 2 | LTO (`-DCOMPILE_LTO=ON` + `-flto` at demo compile/link) | small | Medium | Must verify static-glibc link; drop if it fails |
| 3 | Keep target statically linked | neutral (prevents regression) | Low | Static is required for qemu-user here |
| 4 | Strip debug info for artifacts | 0% runtime (file-size hygiene) | Low | Debug info accounts for most file size on both |
| 5 | QEMU micro-tuning (`-cpu max`, extension flags, TB size) | ~0% (tested; no speedup) | Low | Avoid `-one-insn-per-tb` (severe slowdown) |
| 6 | Alternative allocator | negligible under emulation | High | No cross-built allocator available; static target blocks `LD_PRELOAD` |
| 7 | RVV vectorization | 0% | High | No V extension; carry-bound kernels not vectorizable |
| 8 | PGO / bignum cutoff tuning | 0% under emulation | High | Requires native RISC-V hardware to tune/verify |

---

## 6. Notes About Exploration Process

- The second (target) build is **cross-compiled riscv64 and executed under qemu-user** (`qemu-riscv64-static` 8.2.2 via binfmt_misc), per the pipeline directive. This is the source of the dominant target overhead and must be considered when interpreting all target metrics.
- `file(1)` was not installed; binary classification used `readelf`.
- `/proc/sys/fs/binfmt_misc` is not exposed in the container, but binfmt routing is active — verified via `/proc/<pid>/exe → /usr/bin/qemu-riscv64-static` and the binfmt handler process.
- `perf archive` is not available in the installed perf, so no `.tar.bz2` archive / `perf_script_name` / `perf_archive_name` were produced.
- `nice -n -20` could not be applied (container lacks `CAP_SYS_NICE`); both platforms ran at nice 0. CPU frequency fluctuates (`powersave` governor).
- `perf_event_paranoid` is read-only but already `-1`.
- LLС and top-down (Frontend/Backend Bound, Retiring) counters are not supported by the host PMU; they are reported as NOT AVAILABLE.
- `demo/timing.c` (optional legacy benchmark) is not portable to riscv64 because its `TIMFUNC()` falls into an IA64 assembly `#else` branch; it is not built by CMake/CTest, so it did not affect the build or tests.
- Baseline build directories `1_1_1` / `1_2_2` were preserved and were not rebuilt; optimized builds `1_1_3` / `1_2_4` were added separately.
- The authoritative project data file is `/work/libtommath.json`; it contains all four builds merged.

---

## 7. Migration Readiness Summary

| Criterion | Status |
|---|---|
| Builds on reference | **YES** (`1_1_1`, `1_1_3`) |
| Tests pass on reference | **YES** (50/50) |
| Builds on target | **YES** (`1_2_2`, `1_2_4`) |
| Tests pass on target | **YES** (50/50 under qemu-user) |
| Zero external dependencies | **YES** |
| No hand-written intrinsics | **YES** |
| Alignment safe | **YES** (runtime endianness detection; no compile-time assumptions) |
| Exceptions handled | **N/A** (pure C) |
| Auto-vectorization | Partial — x86 harness code auto-vectorized; none on rv64gc (no V extension) |

### Migration Verdict: **READY**

libtommath is a portable, self-contained scalar C library that builds and passes its full 50-test suite on riscv64 (including under qemu-user). It has no external dependencies and no hand-written SIMD intrinsics. The only portability defect found (`demo/timing.c` `TIMFUNC()` IA64 fallback) is in an optional benchmark that is not part of the CMake/CTest build, and the only soft-float caveat would silently omit `mp_set_double`.

### Required Actions

1. Do not enable `make timing` on riscv64 (or patch `TIMFUNC()` to use `clock_gettime()`/RISC-V `rdtime`) — it currently fails to compile.
2. If targeting a soft-float ABI, confirm whether `mp_set_double` / `MP_HAS_SET_DOUBLE` must be provided explicitly.
3. Performance readiness must be assessed on **native RISC-V hardware**; the qemu-user wall-clock (including the measured improvement) is dominated by emulation overhead and is not representative.
4. Optional: apply the optimizer recommendations (Priority 1 already applied; LTO optionally next).

---

## Recorded Project Data

The following is the recorded project data from `/work/libtommath.json`.

```json
{
  "1_2_4": {
    "demo/test-ltm": {
      "build_name": "1_2_4",
      "executable": "demo/test-ltm",
      "executable_run_success": true,
      "real_time": "39.98",
      "user_time": "39.96",
      "kernel_time": "0.01",
      "perf_stat": [
        {
          "counter_value": "40257.31",
          "unit": "msec",
          "event": "task-clock",
          "event-runtime": "40257307675",
          "pcnt-running": "100.00",
          "metric-value": "1.000",
          "metric-unit": "CPUs utilized"
        },
        {
          "counter_value": "488",
          "event": "context-switches",
          "event-runtime": "40257307675",
          "pcnt-running": "100.00",
          "metric-value": "12.122",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "1",
          "event": "cpu-migrations",
          "event-runtime": "40257307675",
          "pcnt-running": "100.00",
          "metric-value": "0.025",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "1329",
          "event": "page-faults",
          "event-runtime": "40257307675",
          "pcnt-running": "100.00",
          "metric-value": "33.013",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "190838923370",
          "event": "cycles",
          "event-runtime": "14377319137",
          "pcnt-running": "35.00",
          "metric-value": "4.740",
          "metric-unit": "GHz"
        },
        {
          "counter_value": "10322890352",
          "event": "stalled-cycles-frontend",
          "event-runtime": "14376297994",
          "pcnt-running": "35.00",
          "metric-value": "5.41",
          "metric-unit": "frontend cycles idle"
        },
        {
          "counter_value": "891842800548",
          "event": "instructions",
          "event-runtime": "14378348285",
          "pcnt-running": "35.00",
          "metric-value": "4.67",
          "metric-unit": "insn per cycle"
        },
        {
          "metric-value": "0.01",
          "metric-unit": "stalled cycles per insn"
        },
        {
          "counter_value": "128889687524",
          "event": "branches",
          "event-runtime": "14377026349",
          "pcnt-running": "35.00",
          "metric-value": "3.202",
          "metric-unit": "G/sec"
        },
        {
          "counter_value": "100248358",
          "event": "branch-misses",
          "event-runtime": "14378500973",
          "pcnt-running": "35.00",
          "metric-value": "0.08",
          "metric-unit": "of all branches"
        },
        {
          "counter_value": "295995712518",
          "event": "L1-dcache-loads",
          "event-runtime": "14377965037",
          "pcnt-running": "35.00",
          "metric-value": "7.353",
          "metric-unit": "G/sec"
        },
        {
          "counter_value": "856008733",
          "event": "L1-dcache-load-misses",
          "event-runtime": "14378978393",
          "pcnt-running": "35.00",
          "metric-value": "0.29",
          "metric-unit": "of all L1-dcache accesses"
        },
        {
          "counter_value": "<not supported>",
          "event": "LLC-loads",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        },
        {
          "counter_value": "<not supported>",
          "event": "LLC-load-misses",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        },
        {
          "counter_value": "15946263228",
          "event": "L1-icache-loads",
          "event-runtime": "14376878422",
          "pcnt-running": "35.00",
          "metric-value": "396.109",
          "metric-unit": "M/sec"
        },
        {
          "counter_value": "175624049",
          "event": "L1-icache-load-misses",
          "event-runtime": "14378111031",
          "pcnt-running": "35.00",
          "metric-value": "1.10",
          "metric-unit": "of all L1-icache accesses"
        },
        {
          "counter_value": "400704453",
          "event": "dTLB-loads",
          "event-runtime": "14376858464",
          "pcnt-running": "35.00",
          "metric-value": "9.954",
          "metric-unit": "M/sec"
        },
        {
          "counter_value": "1195874",
          "event": "dTLB-load-misses",
          "event-runtime": "14378158412",
          "pcnt-running": "35.00",
          "metric-value": "0.30",
          "metric-unit": "of all dTLB cache accesses"
        },
        {
          "counter_value": "210837636",
          "event": "iTLB-loads",
          "event-runtime": "14377074420",
          "pcnt-running": "35.00",
          "metric-value": "5.237",
          "metric-unit": "M/sec"
        },
        {
          "counter_value": "445688",
          "event": "iTLB-load-misses",
          "event-runtime": "14378168211",
          "pcnt-running": "35.00",
          "metric-value": "0.21",
          "metric-unit": "of all iTLB cache accesses"
        },
        {
          "counter_value": "19341711",
          "event": "L1-dcache-prefetches",
          "event-runtime": "14376853247",
          "pcnt-running": "35.00",
          "metric-value": "480.452",
          "metric-unit": "K/sec"
        },
        {
          "counter_value": "<not supported>",
          "event": "L1-dcache-prefetch-misses",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        }
      ],
      "perf_record_name": "1__2__4..demo_stest-ltm.perfdata",
      "perf_script_name": null,
      "perf_archive_name": null
    }
  },
  "1_1_3": {
    "demo/test-ltm": {
      "build_name": "1_1_3",
      "executable": "demo/test-ltm",
      "executable_run_success": true,
      "real_time": "3.99",
      "user_time": "3.98",
      "kernel_time": "0.00",
      "perf_stat": [
        {
          "counter_value": "4088.63",
          "unit": "msec",
          "event": "task-clock",
          "event-runtime": "4088634802",
          "pcnt-running": "100.00",
          "metric-value": "1.000",
          "metric-unit": "CPUs utilized"
        },
        {
          "counter_value": "47",
          "event": "context-switches",
          "event-runtime": "4088634802",
          "pcnt-running": "100.00",
          "metric-value": "11.495",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "0",
          "event": "cpu-migrations",
          "event-runtime": "4088634802",
          "pcnt-running": "100.00",
          "metric-value": "0.000",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "347",
          "event": "page-faults",
          "event-runtime": "4088634802",
          "pcnt-running": "100.00",
          "metric-value": "84.869",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "19459314151",
          "event": "cycles",
          "event-runtime": "1460397223",
          "pcnt-running": "35.00",
          "metric-value": "4.759",
          "metric-unit": "GHz"
        },
        {
          "counter_value": "1100545378",
          "event": "stalled-cycles-frontend",
          "event-runtime": "1461073331",
          "pcnt-running": "35.00",
          "metric-value": "5.66",
          "metric-unit": "frontend cycles idle"
        },
        {
          "counter_value": "80584578379",
          "event": "instructions",
          "event-runtime": "1461082170",
          "pcnt-running": "35.00",
          "metric-value": "4.14",
          "metric-unit": "insn per cycle"
        },
        {
          "metric-value": "0.01",
          "metric-unit": "stalled cycles per insn"
        },
        {
          "counter_value": "14256653966",
          "event": "branches",
          "event-runtime": "1461103954",
          "pcnt-running": "35.00",
          "metric-value": "3.487",
          "metric-unit": "G/sec"
        },
        {
          "counter_value": "27397117",
          "event": "branch-misses",
          "event-runtime": "1461065162",
          "pcnt-running": "35.00",
          "metric-value": "0.19",
          "metric-unit": "of all branches"
        },
        {
          "counter_value": "21973040385",
          "event": "L1-dcache-loads",
          "event-runtime": "1460454351",
          "pcnt-running": "35.00",
          "metric-value": "5.374",
          "metric-unit": "G/sec"
        },
        {
          "counter_value": "7452860",
          "event": "L1-dcache-load-misses",
          "event-runtime": "1459759499",
          "pcnt-running": "35.00",
          "metric-value": "0.03",
          "metric-unit": "of all L1-dcache accesses"
        },
        {
          "counter_value": "<not supported>",
          "event": "LLC-loads",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        },
        {
          "counter_value": "<not supported>",
          "event": "LLC-load-misses",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        },
        {
          "counter_value": "417866380",
          "event": "L1-icache-loads",
          "event-runtime": "1459805025",
          "pcnt-running": "35.00",
          "metric-value": "102.202",
          "metric-unit": "M/sec"
        },
        {
          "counter_value": "956459",
          "event": "L1-icache-load-misses",
          "event-runtime": "1459747068",
          "pcnt-running": "35.00",
          "metric-value": "0.23",
          "metric-unit": "of all L1-icache accesses"
        },
        {
          "counter_value": "550548",
          "event": "dTLB-loads",
          "event-runtime": "1459787478",
          "pcnt-running": "35.00",
          "metric-value": "134.653",
          "metric-unit": "K/sec"
        },
        {
          "counter_value": "21916",
          "event": "dTLB-load-misses",
          "event-runtime": "1459739919",
          "pcnt-running": "35.00",
          "metric-value": "3.98",
          "metric-unit": "of all dTLB cache accesses"
        },
        {
          "counter_value": "7903",
          "event": "iTLB-loads",
          "event-runtime": "1459755842",
          "pcnt-running": "35.00",
          "metric-value": "1.933",
          "metric-unit": "K/sec"
        },
        {
          "counter_value": "26432",
          "event": "iTLB-load-misses",
          "event-runtime": "1459652919",
          "pcnt-running": "35.00",
          "metric-value": "334.46",
          "metric-unit": "of all iTLB cache accesses"
        },
        {
          "counter_value": "2226371",
          "event": "L1-dcache-prefetches",
          "event-runtime": "1459750069",
          "pcnt-running": "35.00",
          "metric-value": "544.527",
          "metric-unit": "K/sec"
        },
        {
          "counter_value": "<not supported>",
          "event": "L1-dcache-prefetch-misses",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        }
      ],
      "perf_record_name": "1__1__3..demo_stest-ltm.perfdata",
      "perf_script_name": null,
      "perf_archive_name": null
    }
  },
  "1_2_2": {
    "demo/test-ltm": {
      "build_name": "1_2_2",
      "executable": "demo/test-ltm",
      "executable_run_success": true,
      "real_time": "42.69",
      "user_time": "42.67",
      "kernel_time": "0.01",
      "perf_stat": [
        {
          "counter_value": "41853.06",
          "unit": "msec",
          "event": "task-clock",
          "event-runtime": "41853062404",
          "pcnt-running": "100.00",
          "metric-value": "1.000",
          "metric-unit": "CPUs utilized"
        },
        {
          "counter_value": "443",
          "event": "context-switches",
          "event-runtime": "41853062404",
          "pcnt-running": "100.00",
          "metric-value": "10.585",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "1",
          "event": "cpu-migrations",
          "event-runtime": "41853062404",
          "pcnt-running": "100.00",
          "metric-value": "0.024",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "1324",
          "event": "page-faults",
          "event-runtime": "41853062404",
          "pcnt-running": "100.00",
          "metric-value": "31.634",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "198479817367",
          "event": "cycles",
          "event-runtime": "14946620350",
          "pcnt-running": "35.00",
          "metric-value": "4.742",
          "metric-unit": "GHz"
        },
        {
          "counter_value": "10754837091",
          "event": "stalled-cycles-frontend",
          "event-runtime": "14945736398",
          "pcnt-running": "35.00",
          "metric-value": "5.42",
          "metric-unit": "frontend cycles idle"
        },
        {
          "counter_value": "950927995758",
          "event": "instructions",
          "event-runtime": "14947433609",
          "pcnt-running": "35.00",
          "metric-value": "4.79",
          "metric-unit": "insn per cycle"
        },
        {
          "metric-value": "0.01",
          "metric-unit": "stalled cycles per insn"
        },
        {
          "counter_value": "137490955700",
          "event": "branches",
          "event-runtime": "14946912025",
          "pcnt-running": "35.00",
          "metric-value": "3.285",
          "metric-unit": "G/sec"
        },
        {
          "counter_value": "114234316",
          "event": "branch-misses",
          "event-runtime": "14948812987",
          "pcnt-running": "35.00",
          "metric-value": "0.08",
          "metric-unit": "of all branches"
        },
        {
          "counter_value": "314123538581",
          "event": "L1-dcache-loads",
          "event-runtime": "14948236016",
          "pcnt-running": "35.00",
          "metric-value": "7.505",
          "metric-unit": "G/sec"
        },
        {
          "counter_value": "463434889",
          "event": "L1-dcache-load-misses",
          "event-runtime": "14949010100",
          "pcnt-running": "35.00",
          "metric-value": "0.15",
          "metric-unit": "of all L1-dcache accesses"
        },
        {
          "counter_value": "<not supported>",
          "event": "LLC-loads",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        },
        {
          "counter_value": "<not supported>",
          "event": "LLC-load-misses",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        },
        {
          "counter_value": "16460388413",
          "event": "L1-icache-loads",
          "event-runtime": "14947309885",
          "pcnt-running": "35.00",
          "metric-value": "393.290",
          "metric-unit": "M/sec"
        },
        {
          "counter_value": "233609219",
          "event": "L1-icache-load-misses",
          "event-runtime": "14948340654",
          "pcnt-running": "35.00",
          "metric-value": "1.42",
          "metric-unit": "of all L1-icache accesses"
        },
        {
          "counter_value": "400023871",
          "event": "dTLB-loads",
          "event-runtime": "14947387356",
          "pcnt-running": "35.00",
          "metric-value": "9.558",
          "metric-unit": "M/sec"
        },
        {
          "counter_value": "1250800",
          "event": "dTLB-load-misses",
          "event-runtime": "14948254279",
          "pcnt-running": "35.00",
          "metric-value": "0.31",
          "metric-unit": "of all dTLB cache accesses"
        },
        {
          "counter_value": "186608446",
          "event": "iTLB-loads",
          "event-runtime": "14947450603",
          "pcnt-running": "35.00",
          "metric-value": "4.459",
          "metric-unit": "M/sec"
        },
        {
          "counter_value": "209952",
          "event": "iTLB-load-misses",
          "event-runtime": "14947890019",
          "pcnt-running": "35.00",
          "metric-value": "0.11",
          "metric-unit": "of all iTLB cache accesses"
        },
        {
          "counter_value": "18366560",
          "event": "L1-dcache-prefetches",
          "event-runtime": "14945917739",
          "pcnt-running": "35.00",
          "metric-value": "438.834",
          "metric-unit": "K/sec"
        },
        {
          "counter_value": "<not supported>",
          "event": "L1-dcache-prefetch-misses",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        }
      ],
      "perf_record_name": "1__2__2..demo_stest-ltm.perfdata",
      "perf_script_name": null,
      "perf_archive_name": null
    }
  },
  "1_1_1": {
    "demo/test-ltm": {
      "build_name": "1_1_1",
      "executable": "demo/test-ltm",
      "executable_run_success": true,
      "real_time": "3.84",
      "user_time": "3.83",
      "kernel_time": "0.00",
      "perf_stat": [
        {
          "counter_value": "3769.09",
          "unit": "msec",
          "event": "task-clock",
          "event-runtime": "3769087812",
          "pcnt-running": "100.00",
          "metric-value": "1.000",
          "metric-unit": "CPUs utilized"
        },
        {
          "counter_value": "48",
          "event": "context-switches",
          "event-runtime": "3769087812",
          "pcnt-running": "100.00",
          "metric-value": "12.735",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "1",
          "event": "cpu-migrations",
          "event-runtime": "3769087812",
          "pcnt-running": "100.00",
          "metric-value": "0.265",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "348",
          "event": "page-faults",
          "event-runtime": "3769087812",
          "pcnt-running": "100.00",
          "metric-value": "92.330",
          "metric-unit": "/sec"
        },
        {
          "counter_value": "17731142921",
          "event": "cycles",
          "event-runtime": "1345310168",
          "pcnt-running": "35.00",
          "metric-value": "4.704",
          "metric-unit": "GHz"
        },
        {
          "counter_value": "966234982",
          "event": "stalled-cycles-frontend",
          "event-runtime": "1346315348",
          "pcnt-running": "35.00",
          "metric-value": "5.45",
          "metric-unit": "frontend cycles idle"
        },
        {
          "counter_value": "76645931455",
          "event": "instructions",
          "event-runtime": "1347542938",
          "pcnt-running": "35.00",
          "metric-value": "4.32",
          "metric-unit": "insn per cycle"
        },
        {
          "metric-value": "0.01",
          "metric-unit": "stalled cycles per insn"
        },
        {
          "counter_value": "13659687159",
          "event": "branches",
          "event-runtime": "1348406126",
          "pcnt-running": "35.00",
          "metric-value": "3.624",
          "metric-unit": "G/sec"
        },
        {
          "counter_value": "26116188",
          "event": "branch-misses",
          "event-runtime": "1348587387",
          "pcnt-running": "35.00",
          "metric-value": "0.19",
          "metric-unit": "of all branches"
        },
        {
          "counter_value": "20838248442",
          "event": "L1-dcache-loads",
          "event-runtime": "1348032820",
          "pcnt-running": "35.00",
          "metric-value": "5.529",
          "metric-unit": "G/sec"
        },
        {
          "counter_value": "6896251",
          "event": "L1-dcache-load-misses",
          "event-runtime": "1346997497",
          "pcnt-running": "35.00",
          "metric-value": "0.03",
          "metric-unit": "of all L1-dcache accesses"
        },
        {
          "counter_value": "<not supported>",
          "event": "LLC-loads",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        },
        {
          "counter_value": "<not supported>",
          "event": "LLC-load-misses",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        },
        {
          "counter_value": "363227654",
          "event": "L1-icache-loads",
          "event-runtime": "1345852851",
          "pcnt-running": "35.00",
          "metric-value": "96.370",
          "metric-unit": "M/sec"
        },
        {
          "counter_value": "426653",
          "event": "L1-icache-load-misses",
          "event-runtime": "1344903871",
          "pcnt-running": "35.00",
          "metric-value": "0.12",
          "metric-unit": "of all L1-icache accesses"
        },
        {
          "counter_value": "274289",
          "event": "dTLB-loads",
          "event-runtime": "1344697130",
          "pcnt-running": "35.00",
          "metric-value": "72.773",
          "metric-unit": "K/sec"
        },
        {
          "counter_value": "18223",
          "event": "dTLB-load-misses",
          "event-runtime": "1344690602",
          "pcnt-running": "35.00",
          "metric-value": "6.64",
          "metric-unit": "of all dTLB cache accesses"
        },
        {
          "counter_value": "6317",
          "event": "iTLB-loads",
          "event-runtime": "1344672576",
          "pcnt-running": "35.00",
          "metric-value": "1.676",
          "metric-unit": "K/sec"
        },
        {
          "counter_value": "29810",
          "event": "iTLB-load-misses",
          "event-runtime": "1344715869",
          "pcnt-running": "35.00",
          "metric-value": "471.90",
          "metric-unit": "of all iTLB cache accesses"
        },
        {
          "counter_value": "2125829",
          "event": "L1-dcache-prefetches",
          "event-runtime": "1344713877",
          "pcnt-running": "35.00",
          "metric-value": "564.017",
          "metric-unit": "K/sec"
        },
        {
          "counter_value": "<not supported>",
          "event": "L1-dcache-prefetch-misses",
          "event-runtime": "0",
          "pcnt-running": "100.00"
        }
      ],
      "perf_record_name": "1__1__1..demo_stest-ltm.perfdata",
      "perf_script_name": null,
      "perf_archive_name": null
    }
  }
}
```
