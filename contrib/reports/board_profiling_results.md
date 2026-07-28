# RISC-V Board Profiling Results

**Date:** $(date)
**Board:** Spacemit X60 (8-core RISC-V64)
**CPU Core Pinned:** core 0 (taskset -c 0)
**Test Filter:** `[.[] | select(.nested.level1.level2.level3 > 500) | {id, name, sum: (.values | add)}] | sort_by(.sum) | reverse | .[:100]`
**Input:** test_input_large.json (3.6MB)

---

## 1. jq Filter Benchmark (test_filter.jq on test_input_large.json)

All values are averages of 3 runs. Cache counters use L1-dcache events (hardware cache-references/misses not supported on Spacemit X60).

| Variant | Cycles | Instructions | IPC | L1-dcache Loads | L1-dcache Miss Rate | Branch Misses | Page Faults | Time (s) |
|---------|--------|-------------|-----|-----------------|---------------------|---------------|-------------|----------|
| O2 | 1,471,797,473 | 1,160,326,794 | 0.79 | 243,912,773 | 0.91% | 3,785,935 | 9,147 | 0.92 |
| O2-flto | 1,504,231,542 | 1,115,990,643 | 0.74 | 243,530,324 | 0.92% | 4,913,977 | 9,147 | 1.67 |
| O2-flto-no-vector | 1,532,675,976 | 1,110,814,246 | 0.72 | 242,582,352 | 0.96% | 4,768,313 | 9,146 | 2.18 |
| O2-no-vector | 1,523,097,755 | 1,160,863,821 | 0.76 | 246,350,431 | 0.90% | 4,365,104 | 9,146 | 1.94 |
| O3 | 1,546,233,858 | 1,102,732,878 | 0.71 | 233,610,185 | 0.98% | 5,551,989 | 9,149 | 3.87 |
| O3-flto | 1,545,221,458 | 1,088,592,300 | 0.70 | 231,125,776 | 1.00% | 5,670,211 | 9,149 | 3.87 |
| O3-flto-no-vector | 1,501,272,212 | 1,078,876,085 | 0.72 | 230,743,496 | 0.99% | 5,697,485 | 9,147 | 3.79 |
| O3-no-vector | 1,533,212,077 | 1,099,375,816 | 0.72 | 235,901,827 | 0.94% | 5,514,412 | 9,148 | 3.85 |

### Key Observations (Filter Benchmark)

- **O2 is fastest** on the real board (~0.92s), O3 variants are ~4x slower (~3.8s)
- **IPC is very low** (0.70-0.79) — indicating heavy memory stalls on real hardware
- **L1-dcache miss rate** is very low (~0.9-1.0%) — cache is not the bottleneck
- **Branch misses** are higher for O3 variants (~5.5M vs ~3.8-4.9M for O2)
- **Page faults** are identical across all variants (9,146-9,149)

---

## 2. Full Test Suite (jqtest)

Single run per variant (550 tests).

| Variant | Cycles | Instructions | IPC | L1-dcache Loads | L1-dcache Miss Rate | Branch Misses | Page Faults | Time (s) |
|---------|--------|-------------|-----|-----------------|---------------------|---------------|-------------|----------|
| O2 | 6,916,582,459 | 5,078,078,316 | 0.73 | 1,226,163,555 | 1.48% | 27,282,216 | 7,319 | 4.32 |
| O2-flto | 7,505,398,581 | 4,831,298,105 | 0.64 | 1,184,025,443 | 1.60% | 30,170,442 | 7,678 | 13.35 |
| O2-flto-no-vector | 7,641,018,817 | 4,806,642,937 | 0.63 | 1,208,309,975 | 1.54% | 29,857,209 | 7,671 | 13.54 |
| O2-no-vector | 7,587,776,458 | 5,073,573,882 | 0.67 | 1,234,481,764 | 1.54% | 29,139,835 | 7,318 | 12.56 |
| O3 | 7,336,757,113 | 4,914,687,937 | 0.67 | 1,184,311,815 | 1.57% | 28,709,126 | 7,399 | 11.01 |
| O3-flto | 7,538,486,257 | 4,658,604,169 | 0.62 | 1,136,455,899 | 1.65% | 30,467,808 | 7,709 | 15.43 |
| O3-flto-no-vector | 7,506,666,143 | 4,664,828,088 | 0.62 | 1,138,201,750 | 1.70% | 30,918,036 | 7,710 | 15.34 |
| O3-no-vector | 7,630,355,455 | 4,927,456,327 | 0.65 | 1,187,180,442 | 1.66% | 29,151,182 | 7,402 | 14.51 |

### Key Observations (Test Suite)

- **O2 (plain) is dramatically faster** than all other variants on the test suite (4.3s vs 11-15s)
- **IPC drops to 0.62-0.73** under the full test suite — even more memory-bound
- **L1-dcache miss rate** increases slightly (~1.5-1.7%) under full test load

---

## Notes

- `cache-references` and `cache-misses` (generic HW counters) returned `<not counted>` on the Spacemit X60. L1-dcache-specific counters were used instead.
- All runs pinned to CPU core 0 via `taskset -c 0`.
- The O3-flto benchmark shows high variance (31.96% CI on time) — likely due to thermal throttling or background processes during one of the 3 runs.
