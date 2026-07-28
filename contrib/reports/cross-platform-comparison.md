# Cross-Platform Comparison

## x86-64 vs riscv64: JSON Workload (O2 baseline)

| Metric | x86-64 (O2) | riscv64 (O2) | Ratio (riscv/x86) |
|---|---|---|---|
| Time (wall) | 0.182s | 2.043s | 11.2x |
| Cycles | 751M | 8,666M | 11.5x |
| Instructions | 1,209M | 21,000M | 17.4x |
| IPC | 1.61 | 2.42 | 1.5x (QEMU inflated) |
| Cache References | 20.1M | 607M | 30.2x |
| Cache Miss Rate | 14.10% | 9.19% | 0.65x |
| Branch Misses | 4.17M | 14.85M | 3.6x |
| Page Faults | 11,323 | 11,033 | 1.0x |

## Best Optimized Comparison (O3-flto)

| Metric | x86-64 (O3-flto) | riscv64 (O3-flto) | Ratio (riscv/x86) |
|---|---|---|---|
| Time (wall) | 0.172s | 1.775s | 10.3x |
| Cycles | 711M | 7,183M | 10.1x |
| Instructions | 1,113M | 17,898M | 16.1x |
| IPC | 1.57 | 2.49 | 1.6x |
| Cache References | 21.0M | 513M | 24.4x |
| Cache Miss Rate | 13.41% | 5.25% | 0.39x |
| Branch Misses | 4.15M | 11.64M | 2.8x |

## Best RISC-V: O3-flto-no-vector

| Metric | x86-64 (O3-flto) | riscv64 (O3-flto-no-vector) | Ratio |
|---|---|---|---|
| Time (wall) | 0.172s | 1.620s | 9.4x |
| Cycles | 711M | 6,602M | 9.3x |
| Instructions | 1,113M | 15,837M | 14.2x |

## Optimization Impact Comparison

### x86-64: O2 baseline vs O3-flto (best)
- Time: 0.182s → 0.172s (**-5.5%**)
- Cycles: 751M → 711M (-5.3%)
- Instructions: 1,209M → 1,113M (-7.9%)

### riscv64: O2 baseline vs O3-flto (best)
- Time: 2.043s → 1.775s (**-13.1%**)
- Cycles: 8,666M → 7,183M (-17.1%)
- Instructions: 21,000M → 17,898M (-14.8%)

### riscv64: O3-flto vs O3-flto-no-vector (overall best)
- Time: 1.775s → 1.620s (**-8.7%**)
- Cycles: 7,183M → 6,602M (-8.1%)
- Instructions: 17,898M → 15,837M (-11.5%)

## Causal Analysis

### Why riscv64 is slower under QEMU
1. **TCG translation overhead**: Each RISC-V instruction is decoded and translated into 4-10 host x86-64 instructions
2. **No hardware acceleration**: No native RISC-V instruction execution
3. **Memory ordering**: QEMU emulates RISC-V memory model differently from actual hardware
4. **No branch prediction**: QEMU cannot use the host CPU's branch predictor for guest code

### Why LTO helps riscv64 more than x86-64
LTO enables cross-translation-unit inlining. On RISC-V, function calls use the `jal` instruction which saves/restores registers. Inlining eliminates this overhead. The RISC-V calling convention is more register-heavy (16 integer registers for arguments/returns) making call overhead proportionally larger.

### Why no-vector helps riscv64 but not x86-64
x86-64 jq binaries contain zero SIMD instructions — jq's workload doesn't trigger auto-vectorization on x86. However, the RISC-V compiler generates vector instructions (1535-4685 per binary) for string operations and data copying. These vector instructions:
- Increase I-cache footprint (each vector instruction is 4 bytes, same as scalar)
- Are not efficiently used for jq's pointer-chasing workload
- Add overhead for setting up vector configuration (vsetvli instructions)
