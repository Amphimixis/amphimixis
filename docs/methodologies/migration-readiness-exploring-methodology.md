# METHODOLOGY FOR EXPLORING PROJECT READINESS FOR MIGRATION TO A DIFFERENT ARCHITECTURE

> This guide assumes maintaining a report to document key findings for each project under study. Nearly every section is highlighted for inclusion in the report

1. Finding the active repository:
   - check the dates of the latest commits and issues
   - review the description and README in case the project was moved to another repository as part of a larger project (e.g., `RapidXML` moved to `Boost`); in that case, check if the project can be built standalone, without the parent project
   - check for other repositories maintained and developed by other developers; if two forks evolve in parallel, one version may be more advanced
   - look for stable releases, GitHub version tags, etc.
   - also see Debian, Arch, Yocto patches, etc.

2. After selecting an active repository, examine its structure and assess maintainability and complexity:
   - presence of tests, CI, build systems, documentation, benchmarks
   - presence of vectorization macros and other platform-dependent macros in the code; verify their semantics — macro names can sometimes be misleading
   - assess dependencies:
      - dependency count
      - for each dependency check its migration readiness status in database (any resource that contains information about project portability); if project is missing, add the issue in the report, evaluate the portability of this dependency on explored architecture and release your result in the database and report
      - summarize over all dependencies

3. To evaluate package behavior on the explored architecture, build and verify it on the main platform where the project is distributing  (typically x86):
   - build with debug info, optimizations, maybe options for building tests: for optimizations use `-O3` and `-march=<native or supported extensions>` options for C/C++; use `-march=native` for native compilation, otherwise specify for concrete platform: some RISC-V CPUs with partial RVA23 support may have something like `rv64gc_zba_zbb_zbc_zbs_<...>` extension, — you can find this information in `gcc` or `g++` via `-Q --help=target` options, see "Known valid arguments for -march= option"; for `clang` and `clang++` you can see supported targets via `--print-targets` option and supported extensions via `--target=<target> --print-supported-extensions` options
   - build tests using available methods: usually a config option (like `-DYAML_CPP_BUILD_TESTS=on` for `yaml-cpp`) or build target (`make test`)
   - verify functionality: run tests; if they fail, consult documentation or issues; document findings; report bugs to developers if not already done (e.g., file an issue or submit a patch)

4. Repeat steps from previous paragraph for explored platform.

5. For profiling on each platform use `perf stat` and `perf record`:
   - ensure experimental rigor:
      - Pin the process to a high-performance core (`taskset -c <performance_core_number> <your_executable>` on Linux)
      - Set highest priority (`nice -n -20 <your_executable>` on Linux, requires root)
      - Turn off CPU Turbo Boost for fixing frequency: in Linux for Intel you can write 1 to each state for each core in `/sys/devices/system/cpu/cpu<core number>/cpuidle/state<state number>/disable` and `/sys/devices/system/cpu/intel_pstate/no_turbo`; check current frequency via `cat /sys/devices/system/cpu/cpufreq/policy*/scaling_cur_freq`
   - prefer benchmarks over tests for more illustrative results; if test runtime depends on dataset size, try increasing it
   - before measuring of performance do warmup run: 10-15% of planned runs for performance measurement; it loads the CPU cache, allows Branch-Predictor to learn, stabilizes background processes
   - run `perf stat` via the following command

      ```shell
      nice -n -20 taskset -c <performance_core_number> perf stat -ddd <your_executable> # -ddd (triple -d) gives more info
      ```

      From its output, pay attention to elapsed time, cache-misses, branches (branch-misses), and color-highlighted metrics
   - run `perf record` via the command

      ```shell
      nice -n -20 taskset -c <performance_core_number> perf record <your_executable>
      ```

      After collecting samples, view execution statistics with `perf report`
   - compare execution traces across all build variants: run each build at least 6-10 times to get averaged numbers
   - also you can use `perf stat --repeat N` for N runs and use `--table` with it to create a table of measurements
   - compare builds for the target architecture against a reference platform; include the comparison in the report

6. Attempt to optimize bottlenecks:
   - use your toolchain's `objdump` to look for platform vector instructions; if none found, try compiler vectorization flags (`-ftree-vectorize` for `gcc`/`g++`); if that doesn't help, try a newer toolchain (from your distro repos, specialized vendors like Syntacore, or configure one yourself with `crosstool-NG`); if the project has dependencies that need to be separately downloaded into the toolchain root, try `debootstrap` (on Debian-family distros) or `buildroot`
   - try compile toolchain with static linked `libc`/`libc++` for each platform
   - try a different memory allocator: `mimalloc`, `jemalloc`, `tcmalloc`, etc.; if the issue involves heavy `free` or `delete` calls, use arena allocators
   - build the project with LTO (Link Time Optimization)
   - try optimizing high-load areas identified from `perf report` output

***Share your results, and may the Open Source be with you!***
