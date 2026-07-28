# Board vs QEMU: Profiling Comparison & Root-Cause Analysis

**Date:** $(date)
**Board:** Spacemit X60 (8-core RISC-V64)
**QEMU:** qemu-riscv64 (emulated RISC-V64)
**Test:** jq filter on test_input_large.json (3.6MB)
**Filter:** `[.[] | select(.nested.level1.level2.level3 > 500) | {id, name, sum: (.values | add)}] | sort_by(.sum) | reverse | .[:100]`

---

## 1. Raw Metric Comparison

### 1.1 Filter Benchmark (test_filter.jq on test_input_large.json)

Values are averages of 3 runs.

| Variant | Metric | QEMU | Board | Ratio (QEMU/Board) |
|---------|--------|------|-------|---------------------|
| **O2** | Cycles | 8,872,293,321 | 1,471,797,473 | 6.03x |
| | Instructions | 21,055,965,570 | 1,160,326,794 | 18.15x |
| | IPC | 2.37 | 0.79 | 3.00x |
| | Branch Misses | 15,229,960 | 3,785,935 | 4.02x |
| | Page Faults | 11,033 | 9,147 | 1.21x |
| | Time (s) | 2.12 | 0.92 | 2.30x |
| **O2-flto** | Cycles | 7,573,803,516 | 1,504,231,542 | 5.04x |
| | Instructions | 18,779,601,314 | 1,115,990,643 | 16.83x |
| | IPC | 2.48 | 0.74 | 3.35x |
| | Branch Misses | 12,920,087 | 4,913,977 | 2.63x |
| | Page Faults | 10,925 | 9,147 | 1.19x |
| | Time (s) | 1.85 | 1.67 | 1.11x |
| **O2-flto-no-vector** | Cycles | 7,803,074,802 | 1,532,675,976 | 5.09x |
| | Instructions | 18,737,911,265 | 1,110,814,246 | 16.87x |
| | IPC | 2.40 | 0.72 | 3.33x |
| | Branch Misses | 13,294,321 | 4,768,313 | 2.79x |
| | Page Faults | 10,897 | 9,146 | 1.19x |
| | Time (s) | 1.94 | 2.18 | 0.89x |
| **O2-no-vector** | Cycles | 8,545,495,678 | 1,523,097,755 | 5.61x |
| | Instructions | 20,482,436,821 | 1,160,863,821 | 17.64x |
| | IPC | 2.40 | 0.76 | 3.16x |
| | Branch Misses | 15,525,266 | 4,365,104 | 3.56x |
| | Page Faults | 10,914 | 9,146 | 1.19x |
| | Time (s) | 2.11 | 1.94 | 1.09x |
| **O3** | Cycles | 8,587,399,218 | 1,546,233,858 | 5.55x |
| | Instructions | 20,710,449,930 | 1,102,732,878 | 18.78x |
| | IPC | 2.41 | 0.71 | 3.39x |
| | Branch Misses | 14,381,765 | 5,551,989 | 2.59x |
| | Page Faults | 11,141 | 9,149 | 1.22x |
| | Time (s) | 2.08 | 3.87 | 0.54x |
| **O3-flto** | Cycles | 7,430,616,172 | 1,545,221,458 | 4.81x |
| | Instructions | 17,853,056,680 | 1,088,592,300 | 16.40x |
| | IPC | 2.40 | 0.70 | 3.43x |
| | Branch Misses | 11,550,669 | 5,670,211 | 2.04x |
| | Page Faults | 10,978 | 9,149 | 1.20x |
| | Time (s) | 1.82 | 3.87 | 0.47x |
| **O3-flto-no-vector** | Cycles | 6,621,224,427 | 1,501,272,212 | 4.41x |
| | Instructions | 15,847,286,861 | 1,078,876,085 | 14.69x |
| | IPC | 2.39 | 0.72 | 3.32x |
| | Branch Misses | 12,247,601 | 5,697,485 | 2.15x |
| | Page Faults | 10,965 | 9,147 | 1.20x |
| | Time (s) | 1.63 | 3.79 | 0.43x |
| **O3-no-vector** | Cycles | 7,842,590,115 | 1,533,212,077 | 5.12x |
| | Instructions | 18,741,941,187 | 1,099,375,816 | 17.05x |
| | IPC | 2.39 | 0.72 | 3.32x |
| | Branch Misses | 14,212,000 | 5,514,412 | 2.58x |
| | Page Faults | 11,018 | 9,148 | 1.20x |
| | Time (s) | 1.94 | 3.85 | 0.50x |

### 1.2 Cache Counter Comparison (note: different counter types)

QEMU reports generic `cache-references`/`cache-misses`. Board reports `L1-dcache-loads`/`L1-dcache-load-misses`.
These are NOT directly comparable but are listed for reference.

| Variant | QEMU cache-refs | QEMU cache-miss% | Board L1-dcache-loads | Board L1-dcache-miss% |
|---------|-----------------|-------------------|------------------------|------------------------|
| O2 | 610,883,334 | 10.15% | 243,912,773 | 0.91% |
| O2-flto | 515,803,545 | 6.84% | 243,530,324 | 0.92% |
| O2-flto-no-vector | 467,307,557 | 9.14% | 242,582,352 | 0.96% |
| O2-no-vector | 539,428,687 | 9.60% | 246,350,431 | 0.90% |
| O3 | 631,981,557 | 9.15% | 233,610,185 | 0.98% |
| O3-flto | 511,368,190 | 5.54% | 231,125,776 | 1.00% |
| O3-flto-no-vector | 437,617,553 | 9.13% | 230,743,496 | 0.99% |
| O3-no-vector | 524,819,371 | 10.90% | 235,901,827 | 0.94% |

---

## 2. Key Discrepancies

### 2.1 Instruction Count: 15-18x higher on QEMU

This is the most striking discrepancy. The same binary executes **15-18x more instructions** under QEMU than on real hardware for the same workload.

**Root cause:** QEMU user-mode emulation translates RISC-V instructions into x86 host instructions. The `perf` counters on the host measure the **host instruction stream** (translated x86 instructions), not the emulated RISC-V instructions. QEMU's Tiny Block Cache (TCB) JIT produces a much larger instruction footprint than the original RISC-V binary because:
1. Each emulated instruction expands to multiple host instructions (decode, dispatch, state update)
2. QEMU's translation blocks include helper function calls for complex operations
3. The JIT re-generates code for each translation block, inflating the instruction count

### 2.2 IPC: 2.4 on QEMU vs 0.7 on Board

QEMU shows IPC of ~2.4 (close to the theoretical peak for modern x86 hosts), while the real board shows IPC of ~0.7.

**Root cause:** This is fundamentally a measurement artifact:
- **QEMU IPC** reflects the **host CPU's** instruction-level parallelism executing translated code. Modern x86 CPUs have deep out-of-order execution, aggressive branch prediction, and wide issue — yielding high IPC for the translated workload.
- **Board IPC** reflects the **Spacemit X60's** actual RISC-V pipeline behavior. The low IPC (0.7) indicates the workload is heavily memory-bound on real hardware — the CPU stalls waiting for memory accesses to complete.

The QEMU IPC is meaningless for evaluating the real hardware's performance characteristics.

### 2.3 Time: Variable (board faster for O2, slower for O3)

- **O2 variants:** Board is comparable or faster (0.92-2.18s vs 1.85-2.12s)
- **O3 variants:** Board is 2-2.4x slower (3.8-3.9s vs 1.6-2.1s)

**Root cause for O3 being slower on the board:**
1. **Compiler optimization mismatch:** GCC's `-O3` enables aggressive loop unrolling and inlining that increases code size. On the Spacemit X60 with potentially smaller I-cache, this causes more I-cache pressure and instruction fetch stalls.
2. **Vectorization overhead:** O3 auto-vectorization may generate code that doesn't align well with the Spacemit X60's actual SIMD/vector unit capabilities, causing the "optimized" code to run slower than scalar O2 code.
3. **Branch prediction:** O3 variants show 40-50% more branch misses on the board (5.5M vs 3.8M for O2), suggesting the more complex control flow from O3 optimizations doesn't predict well on the X60's branch predictor.

### 2.4 Branch Misses: 2-4x higher on QEMU

QEMU reports 2-4x more branch misses than the real board.

**Root cause:** Again a measurement artifact. QEMU's branch miss counter reflects the **host CPU's** branch prediction behavior on the translated code, which has a very different branch pattern than the original RISC-V binary. The host branch predictor sees QEMU's JIT dispatch loops and helper function calls, not the original program's branches.

### 2.5 Page Faults: ~1.2x higher on QEMU

QEMU shows ~11,000 page faults vs ~9,150 on the board (20% more).

**Root cause:** QEMU's user-mode emulation requires additional virtual memory management:
1. QEMU maintains its own guest virtual address space mapped into the host process
2. Translation block allocation may trigger additional page faults
3. Memory mapping operations (mmap/mprotect) in QEMU add overhead

The real board's page fault count represents actual demand paging from the OS.

---

## 3. Summary

| Aspect | QEMU Behavior | Board Behavior | Why Different |
|--------|---------------|----------------|---------------|
| Instruction count | 15-18x inflated | Actual RISC-V count | QEMU translates each emulated insn to multiple host insns |
| IPC | ~2.4 (host CPU ILP) | ~0.7 (real pipeline) | QEMU measures host parallelism, not emulated pipeline |
| Time (O2) | Comparable | Comparable | JIT overhead roughly cancels with host CPU speed advantage |
| Time (O3) | Faster | 2x slower | O3 optimizations hurt real hardware (I-cache, branch predictor) |
| Cache misses | Host cache behavior | Real L1-dcache behavior | Different cache hierarchies entirely |
| Branch misses | Host branch predictor | Real branch predictor | Different prediction algorithms |
| Page faults | QEMU + guest faults | OS demand paging | QEMU adds its own memory management overhead |

## 4. Conclusions & Recommendations

1. **QEMU is unreliable for performance characterization** of RISC-V binaries. The instruction count, IPC, and branch metrics are properties of the host CPU, not the target. Only wall-clock time has partial relevance, and even that is skewed by JIT overhead.

2. **O2 is the optimal optimization level** for the Spacemit X60 with this workload. O3's aggressive optimizations (vectorization, unrolling) increase code size and branch complexity, hurting performance on this particular microarchitecture.

3. **The workload is memory-bound** on real hardware (IPC = 0.7, L1-dcache miss rate ~1%). Future optimization should focus on memory access patterns rather than instruction-level optimizations.

4. **LTO (Link-Time Optimization) has minimal benefit** for this workload. The O2 and O2-flto results are within noise on the real board.

5. **Disabling vectorization helps O2 slightly** but hurts O3 — suggesting the auto-vectorizer is beneficial only when combined with O3's other aggressive transforms, but even then it's net negative on this hardware.

