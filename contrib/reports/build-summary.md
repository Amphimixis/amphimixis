# Build Summary

## Environment
- **Host**: Linux x86_64, AMD Ryzen 7 5700U, 8 cores/16 threads, 4.34 GHz boost
- **GCC**: 15.2.0 (Ubuntu) — native x86_64 and riscv64-linux-gnu-gcc
- **QEMU**: qemu-riscv64 10.1.0
- **Build System**: autotools (autoconf/automake/libtool)
- **Dependencies**: Bundled oniguruma (regex), decNumber (arbitrary precision)

## Optimization Flags Tested
| Flag Set | Description |
|---|---|
| O2 | `-O2 -g` |
| O3 | `-O3 -g` |
| O2-flto | `-O2 -flto -g`, LDFLAGS=-flto |
| O3-flto | `-O3 -flto -g`, LDFLAGS=-flto |
| O2-no-vector | `-O2 -fno-tree-vectorize -g` |
| O3-no-vector | `-O3 -fno-tree-vectorize -g` |
| O2-flto-no-vector | `-O2 -flto -fno-tree-vectorize -g`, LDFLAGS=-flto |
| O3-flto-no-vector | `-O3 -flto -fno-tree-vectorize -g`, LDFLAGS=-flto |

## Build Results
All 16 builds (8 per platform) completed successfully.

### Binary Sizes (dynamically linked, with `-g` debug symbols)
| Variant | x86-64 (bytes) | riscv64 (bytes) | Ratio |
|---|---|---|---|
| O2 | 71,552 | 3,064,872 | 42.8x |
| O3 | 81,344 | 4,026,896 | 49.5x |
| O2-flto | 72,032 | 3,200,376 | 44.4x |
| O3-flto | 81,976 | 4,068,792 | 49.6x |
| O2-no-vector | 71,584 | 3,061,232 | 42.8x |
| O3-no-vector | 81,528 | 3,877,600 | 47.5x |
| O2-flto-no-vector | 72,080 | 3,197,344 | 44.4x |
| O3-flto-no-vector | 82,024 | 3,959,392 | 48.3x |

### Observations
- RISC-V binaries are ~43-50x larger than x86-64 binaries (expected: RISC-V has fixed 4-byte instruction encoding vs. x86 variable-length)
- O3 produces ~14% larger code than O2 on x86-64, ~25% larger on riscv64 (more aggressive inlining/unrolling)
- LTO increases binary size slightly on both platforms
- Disabling vectorization has negligible effect on x86-64 code size, ~5% smaller on riscv64 (less vector instruction expansion)

## Build Environment Details
```
RISC-V March: rv64imafdcv_zicbom_zicboz_zicntr_zicond_zicsr_zifencei_zihintpause_zihpm_zfh_zfhmin_zca_zcd_zba_zbb_zbc_zbs_zkt_zve32f_zve32x_zve64d_zve64f_zve64x_zvfh_zvfhmin_zvkt_sscofpmf_sstc_svinval_svnapot_svpbmt
Cross-compiler: riscv64-linux-gnu-gcc 15.2.0
QEMU_LD_PREFIX: /usr/riscv64-linux-gnu/
```
