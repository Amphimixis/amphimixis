# jemalloc + Static Linking: Profiling Results & Comparison

**Date:** $(date)
**Board:** Spacemit X60 (8-core RISC-V64)
**CPU Core Pinned:** core 0 (taskset -c 0)

---

## 1. Build Configuration

| Variant | Optimization | Linking | Allocator | Binary Size (stripped) |
|---------|-------------|---------|-----------|----------------------|
| O2 (baseline) | -O2 | Dynamic | glibc malloc | 3,064,872 bytes |
| O2 + jemalloc | -O2 | Dynamic + LD_PRELOAD | jemalloc 5.3.0 | 3,064,872 bytes (same binary) |

### jemalloc Details
- **Version:** 5.3.0
- **Build flags:** `-march=rv64gc_zicbom_zicboz_zicntr_zicond_zicsr_zifencei_zihintpause_zihpm_zfh_zfhmin_zca_zcd_zba_zbb_zbc_zbs_zkt_sscofpmf_sstc_svinval_svnapot_svpbmt` (no V extension — board crashes on vector instructions despite ISA reporting V support)
- **Linking method:** `LD_PRELOAD=~/pvl-klk/libjemalloc.so.2`
- **Note:** Static linking was attempted but glibc's static library (`libc.a`) contains vector instructions that crash on this board's kernel, so dynamic + LD_PRELOAD was used instead.

---

## 2. Filter Benchmark (test_filter.jq on test_input_large.json)

Values are averages of 3 runs.

| Metric | O2 (glibc) | O2 + jemalloc | Delta | Delta % |
|--------|------------|---------------|-------|---------|
| Cycles | 1,471,797,473 | 1,481,733,915 | +9,936,442 | +0.68% |
| Instructions | 1,160,326,794 | 1,162,273,507 | +1,946,713 | +0.17% |
| IPC | 0.79 | 0.78 | -0.01 | -1.27% |
| L1-dcache Loads | 243,912,773 | 245,891,633 | +1,978,860 | +0.81% |
| L1-dcache Miss Rate | 0.91% | 0.90% | -0.01pp | -1.10% |
| Branch Misses | 3,785,935 | 3,775,644 | -10,291 | -0.27% |
| Page Faults | 9,147 | 9,246 | +99 | +1.08% |
| **Time (s)** | **0.92** | **0.93** | **+0.01** | **+1.09%** |

### Filter Benchmark Assessment
**jemalloc has negligible impact on the filter benchmark** (~1% within noise margin).

---

## 3. Full Test Suite (jqtest, 550 tests)

Single run per variant.

| Metric | O2 (glibc) | O2 + jemalloc | Delta | Delta % |
|--------|------------|---------------|-------|---------|
| Cycles | 6,916,582,459 | 6,962,805,896 | +46,223,437 | +0.67% |
| Instructions | 5,078,078,316 | 5,080,370,494 | +2,292,178 | +0.04% |
| IPC | 0.73 | 0.73 | 0.00 | 0.00% |
| L1-dcache Loads | 1,226,163,555 | 1,226,512,305 | +348,750 | +0.03% |
| L1-dcache Miss Rate | 1.48% | 1.49% | +0.01pp | +0.68% |
| Branch Misses | 27,282,216 | 26,901,964 | -380,252 | -1.39% |
| Page Faults | 7,319 | 7,425 | +106 | +1.45% |
| **Time (s)** | **4.32** | **4.35** | **+0.03** | **+0.70%** |

### Test Suite Assessment
**jemalloc has negligible impact on the test suite** (~0.7% within noise margin). All 550 tests pass.

---

## 4. Analysis: Why jemalloc Has Minimal Impact

### 4.1 jq's Memory Allocation Pattern
jq is a **single-threaded, streaming JSON parser**. Its memory allocation pattern is:
- **Parse phase:** Many small allocations (jv objects, parse tree nodes)
- **Filter phase:** Moderate allocations (intermediate results, output objects)
- **Overall:** Allocation rate is moderate, not allocation-bound

jemalloc excels at:
- **Multi-threaded** workloads (thread cache, arena per-thread)
- **High allocation rate** workloads (reduced lock contention)
- **Fragmentation-prone** workloads (better size-class management)

Since jq is single-threaded and doesn't have extreme allocation pressure, jemalloc's advantages don't apply here.

### 4.2 Workload Is Memory-Bandwidth Bound, Not Allocation-Bound
The profiling data shows:
- **IPC = 0.73** → CPU stalls on memory accesses (not on malloc/free)
- **L1-dcache miss rate = 1.49%** → moderate cache pressure
- **Instructions = 5B** → significant computation between allocations

The bottleneck is **data access patterns** and **memory latency**, not allocator overhead. Optimizing the allocator doesn't help when the CPU is waiting for DRAM.

### 4.3 Static Linking Limitation on This Board
The Spacemit X60 board has a kernel that crashes on vector instructions (SIGILL), despite the ISA string reporting V extension support. Since glibc's static library (`libc.a`) contains vector instructions compiled with V support, static linking is not viable without:
1. A custom glibc build without V instructions
2. A kernel fix for V extension handling
This is documented in the Notes section below.

---

## 5. Executive Summary

| Aspect | Result |
|--------|--------|
| Build success | ✅ Dynamic build + LD_PRELOAD (static not viable) |
| Tests pass | ✅ 550/550 |
| Filter benchmark delta | ~1% (negligible) |
| Test suite delta | ~0.7% (negligible) |
| Recommendation | **jemalloc not recommended for jq on this hardware** |

---

## 6. Notes About This Exploration

1. **Static linking failed** due to glibc vector instructions: The RISC-V cross-compiler's glibc static library (`libc.a`) contains 1,732 vector instructions. These instructions crash with SIGILL (ILL_ILLOPC) on the Spacemit X60 board, despite the ISA string reporting V extension support. This suggests the board's kernel lacks proper V extension trap handling or the X60 CPU doesn't implement all V sub-extensions that glibc assumes.

2. **jemalloc itself has zero vector instructions** when compiled with `-march=rv64gc` (no V), confirming the problem is exclusively in glibc's static library.

3. **LD_PRELOAD was used as fallback**: `LD_PRELOAD=/root/pvl-klk/libjemalloc.so.2 ./O2/jq ...` works correctly and all 550 tests pass.

4. **Static + jemalloc binary had 3,662 vector instructions** — all from glibc, none from jemalloc or jq code.

5. **Conclusion**: For this workload (jq streaming parser), jemalloc does not provide measurable improvement because the bottleneck is memory access latency, not allocator overhead.
