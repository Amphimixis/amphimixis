# Vectorization Analysis

## Method
Binary analysis using `objdump -d` with instruction pattern matching.

## x86-64 Vectorization

| Variant | SSE/AVX Instructions | Notes |
|---|---|---|
| O2 | 4 | Only XORPS for FPU init |
| O3 | 4 | Same — no auto-vectorization |
| O2-flto | 4 | Same |
| O3-flto | 4 | Same |
| O2-no-vector | 4 | Same — no vectors to disable |
| O3-no-vector | 4 | Same |
| O2-flto-no-vector | 4 | Same |
| O3-flto-no-vector | 4 | Same |

**Finding**: jq does NOT auto-vectorize on x86-64 regardless of optimization level. The workload is dominated by:
- Pointer-chasing through JSON tree nodes
- Bytecode interpreter loop (switch/case dispatch)
- Memory allocation and copying
- String comparison (character-by-character)
- Mathematical operations on individual values

None of these patterns are amenable to x86 SIMD auto-vectorization.

## RISC-V Vectorization

| Variant | Vector Instructions | Bit-Manip Instructions | Notes |
|---|---|---|---|
| O2 | 1,535 | 1,552 | Base auto-vectorization |
| O3 | 4,685 | 2,305 | Aggressive vectorization |
| O2-no-vector | 583 | ~similar | Reduced but not zero |
| O3-no-vector | ~similar | ~similar | Reduced |
| O2-flto | ~1,500 | ~similar | LTO doesn't change vectorization |
| O3-flto | ~4,700 | ~similar | LTO + aggressive vectorization |

### Vector Instruction Types Used (RISC-V)
- `vsetvli`: Vector configuration (sets vector length for subsequent operations)
- `vle8.v` / `vle16.v` / `vle32.v` / `vle64.v`: Vector element loads
- `vse8.v` / `vse16.v` / `vse32.v` / `vse64.v`: Vector element stores
- `vadd.vv` / `vsub.vv` / `vmul.vv`: Vector arithmetic
- `vand.vv` / `vor.vv` / `vxor.vv`: Vector bitwise operations
- `vslide1up` / `vslide1down`: Vector sliding operations
- Various mask operations

### Bit-Manipulation Extensions Used (zba/zbb/zbc/zbs)
- `sh1add` / `sh2add` / `sh3add`: Shifted add (zba)
- `clz` / `ctz` / `cpop`: Count leading/trailing zeros, popcount (zbb)
- `rev8`: Byte reverse (zbb)
- `bclr` / `bext` / `binv` / `bset`: Bit manipulation (zbs)
- `pack` / `packh`: Data packing
- `andn` / `orn` / `xnor`: Complemented bitwise operations
- `rol` / `ror`: Rotations

## Why RISC-V Gets Auto-Vectorized but x86 Doesn't

1. **Compiler heuristic differences**: GCC's RISC-V backend is more aggressive with auto-vectorization, using vector instructions for bulk memory operations (string copies, array initialization) that x86 handles with REP MOVS or other scalar/string operations.

2. **String operations**: jq performs many string comparisons and copies. GCC targets these with RVV (RISC-V Vector) for bulk operations.

3. **Data structure initialization**: Object/array creation involves memset-like patterns that GCC vectorizes on RISC-V.

4. **x86 uses different idioms**: On x86, similar operations use SSE/AVX but jq's specific patterns (small, irregular sizes) don't trigger vectorization.

## Impact Assessment

For jq's workload, RISC-V vectorization is **not beneficial**:
- jq operates on individual JSON values (boxes 16-32 bytes each)
- The interpreter loop processes one bytecode at a time
- Data structures are pointer-heavy, not contiguous arrays
- String operations are typically short (key names, small values)

The vector instructions increase code size and I-cache pressure without meaningful runtime benefit. Disabling vectorization with `-fno-tree-vectorize` produces smaller, potentially faster binaries for this workload.
