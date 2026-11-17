# Hall of Fame

Amphimixis helps uncover performance opportunities, portability gaps, and
correctness issues in real-world projects. These patches were found with its
help and submitted to upstream maintainers.

| Project and patch | Finding | Result | Status | Report |
| --- | --- | --- | --- | --- |
| **util-linux**<br>[Faster `hexdump -C`](https://github.com/util-linux/util-linux/pull/4662) | The built-in format made many `printf()` calls per line. | **12.16x faster** in the PR's reported benchmark; byte-identical output. | ✓ Merged | — |
| **libtommath**<br>[RISC-V support for `TIMFUNC`](https://github.com/libtom/libtommath/pull/615) | The demo timing macro lacked 64-bit RISC-V support. | Benchmarks can use `TIMFUNC` on RISC-V architecture. | ○ Open | {doc}`Read report <libtommath-report>` |
| **cJSON**<br>[Fix `__GNUCC__` typo](https://github.com/DaveGamble/cJSON/pull/1096) | `cJSON_Utils.c` checked `__GNUCC__` instead of `__GNUC__`. | Corrects the compiler check for visibility pragmas. | ○ Open | {doc}`Read report <cJSON-report>` |

All project reports are available in [`docs/reports`](https://github.com/Amphimixis/amphimixis/tree/main/docs/reports).

PR states are shown as of November 2026 and may change. See each pull request
for its discussion, checks, and current status.
