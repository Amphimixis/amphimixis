# RISC-V64 Board: Build Deployment, Testing, and Profiling Task

## Objective
Deploy RISC-V64 executables to a target board, run and validate tests, profile
performance under controlled CPU affinity, and compare results against QEMU
to explain any observed differences.

## Environment
- **Board address:** `root@192.168.100.2`
- **Authentication:** none required — SSH access is already configured
  (passwordless / key-based)

---

## 1. Prepare

1. Copy the RISCV64 executables from the local `./build` directory onto the
   board, placing them under `~/pvl-klk/`:
   ```bash
   scp -r ./build/* root@192.168.100.2:~/pvl-klk/
   ```
2. Review existing research/profiling reports located in `./profiling` to
   understand prior results, methodology, and any known baselines before
   starting new work.

---

## 2. Test

1. On the board, run the test suite via `jq`:
   ```bash
   jq tests/<test_name>
   ```
2. Execute this for each relevant test case.
3. **Verify that all tests pass** before proceeding to profiling. Do not
   profile against a build with failing tests — investigate and resolve
   failures first.

---

## 3. Profile

1. Pin each profiled process to a single CPU core using `taskset`:
   ```bash
   taskset -c N <executable> [args...]
   ```
   (choose a consistent core `N` for all runs to keep comparisons valid)
2. Collect hardware performance counters for each run, including:
   - `cycles`
   - `instructions`
   - `cache-references`
   - `cache-misses`
   - `branch-misses`
   - `page-faults`

   Example using `perf`:
   ```bash
   taskset -c N perf stat -e cycles,instructions,cache-references,cache-misses,branch-misses,page-faults <executable>
   ```

---

## 4. Save

- Record all collected profiling data (per test/executable, per metric) into
  a **markdown file stored on the board** for later retrieval.
- Include enough metadata (date, core used, test name, command run) to make
  results reproducible and traceable.

---

## 5. Analyze

1. Compare the board's profiling results against equivalent results obtained
   on **QEMU**.
2. Analyze and explain *why* the metrics differ between the real board and
   QEMU emulation (e.g., differences in cache hierarchy, branch prediction
   accuracy, instruction timing model fidelity, page-fault behavior under
   emulation, etc.).
3. Write the comparison and analysis into a markdown file summarizing:
   - Raw metric comparisons (table format recommended)
   - Key discrepancies
   - Root-cause explanations for each significant difference
   - Any conclusions or recommendations

---

## Deliverables
- [ ] Executables copied to `~/pvl-klk/` on the board
- [ ] All tests passing (via `jq tests/<test_name>`)
- [ ] Profiling data collected (cycles, instructions, cache-references,
      cache-misses, branch-misses, page-faults) with `taskset`-pinned runs
- [ ] Markdown file with raw profiling results saved **on the board**
- [ ] Markdown file with board-vs-QEMU comparison and root-cause analysis
