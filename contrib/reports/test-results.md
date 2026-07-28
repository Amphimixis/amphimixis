# Test Results

## Test Framework
- **Test suite**: 550 tests in `tests/jq.test` (triplet format: program, input, expected output)
- **Additional tests**: `--run-tests` mode with jq_state, jq_compile_args, recompile, exhaust/reuse
- **Modules tested**: tests/modules/ directory with import/include tests
- **Test execution**: `jq --run-tests tests/jq.test` (NOT via `make check`)

## Results Summary
**All 16 build variants pass all 550 tests on both platforms.**

| Platform | Variant | Tests Run | Passed | Failed | Malformed | Skipped | Exit Code |
|---|---|---|---|---|---|---|---|
| x86-64 | O2 | 550 | 550 | 0 | 0 | 0 | 0 |
| x86-64 | O3 | 550 | 550 | 0 | 0 | 0 | 0 |
| x86-64 | O2-flto | 550 | 550 | 0 | 0 | 0 | 0 |
| x86-64 | O3-flto | 550 | 550 | 0 | 0 | 0 | 0 |
| x86-64 | O2-no-vector | 550 | 550 | 0 | 0 | 0 | 0 |
| x86-64 | O3-no-vector | 550 | 550 | 0 | 0 | 0 | 0 |
| x86-64 | O2-flto-no-vector | 550 | 550 | 0 | 0 | 0 | 0 |
| x86-64 | O3-flto-no-vector | 550 | 550 | 0 | 0 | 0 | 0 |
| riscv64 | O2 | 550 | 550 | 0 | 0 | 0 | 0 |
| riscv64 | O3 | 550 | 550 | 0 | 0 | 0 | 0 |
| riscv64 | O2-flto | 550 | 550 | 0 | 0 | 0 | 0 |
| riscv64 | O3-flto | 550 | 550 | 0 | 0 | 0 | 0 |
| riscv64 | O2-no-vector | 550 | 550 | 0 | 0 | 0 | 0 |
| riscv64 | O3-no-vector | 550 | 550 | 0 | 0 | 0 | 0 |
| riscv64 | O2-flto-no-vector | 550 | 550 | 0 | 0 | 0 | 0 |
| riscv64 | O3-flto-no-vector | 550 | 550 | 0 | 0 | 0 | 0 |

## Test Categories Covered
- Parser tests (syntax, escape sequences, Unicode, UTF-8)
- Dictionary/object construction
- Field access and piping
- Array/string slicing
- Variables and destructuring
- Built-in functions (math, string, array, object)
- User-defined functions, closures, recursion
- Reduce, foreach, limit, skip
- Conditionals (if/elif/else/try/catch)
- Assignment operators
- Module system (import/include)
- Path expressions
- Sorting, grouping, uniqueness
- Type checking and conversion
- Date/time functions
- Large value handling (10000+ elements)

## Notes
- RISC-V tests ran under QEMU emulation (`qemu-riscv64 -L /usr/riscv64-linux-gnu`)
- QEMU emulation adds overhead but does not affect test correctness
- Binary precision tests handle both decNumber and float precision
