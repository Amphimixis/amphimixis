# Optimization Recommendations

## Cross-Platform Optimizations (applicable to both targets)

### 1. Use LTO (Link-Time Optimization) — HIGH PRIORITY
**Expected gain**: 5-15% performance improvement
**Effort**: Minimal (add `-flto` to CFLAGS and LDFLAGS)

LTO is the single most effective optimization for jq on both platforms:
- x86-64: 5.5% faster (0.182s → 0.172s)
- riscv64: 13% faster (2.043s → 1.775s)

**How to apply**:
```bash
# In configure step:
CFLAGS="-O3 -flto -g" LDFLAGS="-flto" ./configure ...
```

### 2. Use -O3 over -O2 — LOW PRIORITY
**Expected gain**: 0-5% on x86-64, ~0% on riscv64 (within noise)
**Effort**: None (change flag)

O3 vs O2 shows marginal difference for jq. The bytecode interpreter is the bottleneck, and O3's additional optimizations (loop unrolling, inlining heuristics) don't significantly help.

### 3. Use Custom Allocator — MEDIUM PRIORITY
**Expected gain**: 10-30% for JSON-heavy workloads
**Effort**: Medium (integration work)

jq uses a custom allocator (jv_alloc.c) but could benefit from a more cache-friendly allocator like jemalloc or mimalloc for large JSON processing. The current allocator shows high cache miss rates (~14% on x86).

### 4. Static Linking — LOW PRIORITY
**Expected gain**: 5-10% (eliminates PLT/GOT overhead)
**Effort**: Low

Use `--enable-all-static` or `-static` to produce statically-linked binaries. Eliminates dynamic linker overhead and improves code locality.

## RISC-V Specific Optimizations

### 1. Disable Auto-Vectorization — MEDIUM PRIORITY
**Expected gain**: 5-10% for jq workload
**Effort**: None (add flag)

For jq's pointer-chasing workload, RISC-V vector instructions increase I-cache pressure without benefit. The best RISC-V result (O3-flto-no-vector: 1.62s) beats O3-flto (1.775s) by 8.7%.

**How to apply**:
```bash
CFLAGS="-O3 -flto -fno-tree-vectorize -g" LDFLAGS="-flto" ./configure --host=riscv64-linux-gnu ...
```

### 2. Use Specific Microarchitecture Target — MEDIUM PRIORITY
**Expected gain**: 5-15% on native hardware
**Effort**: None (change flag)

Instead of the extremely broad march string covering all extensions, target a specific RISC-V implementation:
```bash
# For SiFive U74 (common in embedded):
-march=rv64imafdc_zicsr_zifencei

# For SpacemiT K1 (with vector):
-march=rv64imafdcv_zicbom_zicboz_zicsr_zifencei_zve64f
```

A narrower -march string:
- Produces smaller code (fewer extension-specific instructions)
- Enables better scheduling for the specific microarchitecture
- Avoids generating code for extensions the hardware doesn't support

### 3. Leverage Zbb (Bit Manipulation) Extensions — LOW PRIORITY
**Expected gain**: 2-5%
**Effort**: None (already enabled via -march)

The zbb extension provides efficient `clz`, `ctz`, `cpop`, `rev8` instructions useful for string processing. Already enabled in the march string. Verify the target hardware supports these.

### 4. Profile-Guided Optimization (PGO) — HIGH PRIORITY
**Expected gain**: 10-20%
**Effort**: Medium (requires profiling run)

```bash
# Step 1: Compile with profiling
CFLAGS="-O3 -flto -fprofile-generate" ./configure --host=riscv64-linux-gnu ...
make && ./jq < typical_workload.json > /dev/null

# Step 2: Recompile with profile data
CFLAGS="-O3 -flto -fprofile-use" ./configure --host=riscv64-linux-gnu ...
make
```

PGO would help the compiler:
- Optimize branch prediction in the bytecode interpreter
- Inline hot functions more aggressively
- Optimize the memory allocation paths

### 5. Consider Reducing String Operations — LOW PRIORITY
**Expected gain**: 3-8%
**Effort**: High (code changes)

jq performs many string comparisons in the parser and compiler. Using a string interning or hash-based approach for repeated strings could reduce both instruction count and memory traffic.

## Summary Table

| Optimization | Priority | Expected Gain | Effort | Platform |
|---|---|---|---|---|
| Use LTO | HIGH | 5-15% | Minimal | Both |
| Disable RISC-V auto-vectorization | MEDIUM | 5-10% | None | RISC-V |
| Profile-Guided Optimization | HIGH | 10-20% | Medium | Both |
| Custom allocator | MEDIUM | 10-30% | Medium | Both |
| Static linking | LOW | 5-10% | Low | Both |
| Targeted -march | MEDIUM | 5-15% | None | RISC-V |
| Zbb extensions | LOW | 2-5% | None | RISC-V |
| String interning | LOW | 3-8% | High | Both |

## Quick-Start Optimal Build Commands

### x86-64 (optimized)
```bash
./configure CFLAGS="-O3 -flto -g" LDFLAGS="-flto" --disable-docs
make -j$(nproc)
```

### riscv64 (optimized, for typical SiFive-class hardware)
```bash
./configure \
  --host=riscv64-linux-gnu \
  CC=riscv64-linux-gnu-gcc \
  CFLAGS="-O3 -flto -fno-tree-vectorize -march=rv64imafdc_zicsr_zifencei -g" \
  LDFLAGS="-flto" \
  --disable-docs
make -j$(nproc)
```
