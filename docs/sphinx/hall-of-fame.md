# Amphimixis in Open Source

Amphimixis helps uncover performance opportunities, portability gaps, and
small correctness issues in real-world projects. Here are three patches found
with its help and submitted to upstream maintainers.

## util-linux: a faster `hexdump -C`

[hexdump: add single-fwrite fast path for builtin -C](https://github.com/util-linux/util-linux/pull/4662)

The built-in canonical format printed each line through many separate
`printf()` calls. The patch assembles a line in a buffer and writes it with a
single `fwrite()`, while retaining the generic path for other formats and
colored output.

In the pull request's reported `hyperfine` measurement on a 100 MB file, the
optimized version ran **12.16x faster**. Its output was byte-identical to the
original. **Merged.**

## libtommath: RISC-V benchmark support

[bench: add riscv support to TIMFUNC](https://github.com/libtom/libtommath/pull/615)

This patch adds 64-bit RISC-V support to the `TIMFUNC` macro used by the
library's demo timing tests, helping those benchmarks run on another
architecture. **Open.**

## cJSON: fix a compiler macro typo

[Fix: correct `__GNUCC__` typo in cJSON_Utils.c](https://github.com/DaveGamble/cJSON/pull/1096)

The visibility pragmas in `cJSON_Utils.c` checked the misspelled `__GNUCC__`
macro instead of GCC's `__GNUC__`. Correcting the spelling lets the intended
compiler-specific visibility handling take effect. **Open.**

PR states are shown as of November 2026 and may change. See each pull request
for its discussion, checks, and current status.
