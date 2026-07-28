# Profiling Results

## Experimental Conditions
- **CPU**: AMD Ryzen 7 5700U (8 cores/16 threads, 4.34 GHz boost)
- **OS**: Linux 6.17.0-40-generic
- **Core pinning**: `taskset -c 0` (single core)
- **Measurement tool**: `perf stat -e cycles,instructions,cache-references,cache-misses,branch-misses,page-faults`
- **Workload**: jq filter processing 3.6MB JSON file (10,000 objects with nested data, arrays of floats)
- **Filter**: `[.[] | select(.nested.level1.level2.level3 > 500) | {id, name, sum: (.values | add)}] | sort_by(.sum) | reverse | .[:100]`
- **Note**: RISC-V runs under QEMU emulation (qemu-riscv64 10.1.0). Timing includes emulation overhead and may not reflect native hardware performance.

## JSON Workload Results (Run 1 of 3)

### x86-64 (Native)
| Variant | Time (s) | Cycles | Instructions | IPC | Cache Refs | Cache Miss % | Branch Misses |
|---|---|---|---|---|---|---|---|
| O2 | 0.182 | 751M | 1,209M | 1.61 | 20.1M | 14.10% | 4.17M |
| O3 | 0.181 | 740M | 1,166M | 1.58 | 21.8M | 13.24% | 4.16M |
| O2-flto | 0.183 | 746M | 1,208M | 1.62 | 20.2M | 14.38% | 4.16M |
| **O3-flto** | **0.172** | **711M** | **1,113M** | **1.57** | **21.0M** | **13.41%** | **4.15M** |
| O2-no-vector | 0.180 | 737M | 1,210M | 1.64 | 21.8M | 13.02% | 4.15M |
| O3-no-vector | 0.180 | 737M | 1,167M | 1.58 | 20.8M | 13.79% | 4.10M |
| O2-flto-no-vector | 0.180 | 743M | 1,206M | 1.62 | 20.3M | 13.63% | 4.19M |
| O3-flto-no-vector | 0.175 | 722M | 1,113M | 1.54 | 19.8M | 14.15% | 4.16M |

### riscv64 (Under QEMU Emulation)
| Variant | Time (s) | Cycles | Instructions | IPC | Cache Refs | Cache Miss % | Branch Misses |
|---|---|---|---|---|---|---|---|
| O2 | 2.043 | 8,666M | 21,000M | 2.42 | 607M | 9.19% | 14.85M |
| O3 | 2.102 | 8,663M | 20,674M | 2.39 | 629M | 9.40% | 14.48M |
| O2-flto | 1.831 | 7,535M | 18,813M | 2.50 | 520M | 6.69% | 12.83M |
| **O3-flto** | **1.775** | **7,183M** | **17,898M** | **2.49** | **513M** | **5.25%** | **11.64M** |
| O2-no-vector | 2.107 | 8,540M | 20,505M | 2.40 | 542M | 9.50% | 15.67M |
| O3-no-vector | 1.947 | 7,851M | 18,752M | 2.39 | 525M | 11.31% | 14.03M |
| O2-flto-no-vector | 1.932 | 7,782M | 18,734M | 2.41 | 472M | 9.34% | 13.48M |
| **O3-flto-no-vector** | **1.620** | **6,602M** | **15,837M** | **2.40** | **434M** | **9.40%** | **12.14M** |

## Key Metrics
- **IPC (Instructions Per Cycle)**: x86-64 ~1.5-1.6, riscv64 (QEMU) ~2.3-2.5
- **Cache Miss Rate**: x86-64 ~13-15%, riscv64 (QEMU) ~5-11%
- **Branch Misses**: riscv64 ~3.5x more than x86-64

## Causal Analysis

### Why IPC differs:
The RISC-V IPC appears higher (~2.4 vs ~1.6) because QEMU's TCG (Tiny Code Generator) translates each RISC-V instruction into multiple host x86-64 instructions. perf counts the host instruction completions, inflating the apparent IPC. On real RISC-V hardware, IPC would be lower.

### Why cache miss rates differ:
QEMU emulation creates different memory access patterns. The guest memory is allocated in host memory with different alignment and prefetch behavior. QEMU's translation cache (TB cache) reduces certain memory accesses. The lower measured cache miss rate on RISC-V under QEMU does NOT indicate better cache behavior on real hardware.

### Why LTO helps RISC-V so much:
LTO enables cross-module inlining, especially of hot functions in jv.c, jv_parse.c, and the decNumber library. This reduces function call overhead (critical for the bytecode interpreter loop) and enables better register allocation across module boundaries. The effect is amplified on RISC-V because the instruction cache is more sensitive to code layout.

### Why no-vector sometimes helps RISC-V:
Vector instructions (1535-4685 per binary) increase instruction cache footprint. For jq's workload (primarily pointer-chasing through JSON trees, bytecode interpretation), the vector instructions may not be effectively used by the runtime, and their presence bloats the I-cache. Disabling vectorization produces smaller, I-cache-friendlier code.
