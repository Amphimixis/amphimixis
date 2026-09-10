# Usage Examples

> Real-world tasks you can solve with Amphimixis.

This page describes real-world tasks you can solve with Amphimixis, rather
than a fixed set of scenarios.

## Porting an application to RISC-V

This example walks through a typical migration-readiness task: porting a C++
project from x86 to RISC-V. Beyond making the code build and run on the new
architecture, you usually want to know *how* its performance characteristics
change — which functions consume more CPU time, which `perf` events disappear,
and where the new architecture introduces slowdowns.

We use [TinyXML-2](https://github.com/leethomason/tinyxml2) as the target
project and the distributed-cross configuration below. Amphimixis builds and
runs the project natively on both machines, profiles it, and produces a
cross-table that compares the two builds per CPU event.

### Set up the configuration

The project is built and executed on two platforms:

- platform `1` — the local **x86** machine (baseline);
- platform `2` — a remote **RISC-V** machine (the migration target).

```yaml
# distributed.yml
platforms:
- id: 1
  arch: x86

- id: 2
  arch: riscv            # Available: x86, riscv, arm
  address: 10.141.237.177
  username: root
  password: bianbu

recipes:
- id: 1
  config_flags: "-DCMAKE_BUILD_TYPE=RelWithDebInfo"
- id: 2
  config_flags: "-DCMAKE_BUILD_TYPE=RelWithDebInfo"

builds:
- build_machine: 1
  run_machine: 1
  recipe_id: 1
- build_machine: 2
  run_machine: 2
  recipe_id: 2
```

Each build gets an automatically generated name in the form
`build_machine_run_machine_recipe_id`, so our two builds are called:

- `1_1_1` — built and run on **x86**;
- `2_2_2` — built and run on **RISC-V**.

For the full list of supported fields, see the
[Configuration File Guide](config_instruction.md).

### Run the pipeline

```bash
amixis run --config distributed.yml /path/to/tinyxml2
```

Amphimixis analyzes the project, builds it on both machines, profiles the
`xmltest` executable with `perf`, and saves the profiling data as
`.scriptout` files:

```text
2__2__2..xmltest.scriptout   # RISC-V build
1__1__1..xmltest.scriptout   # x86 build
```

> The `_` characters in build names are escaped to `__` in file names so that
> the build name and the executable path stay reversible (see the
> `tools.build_filename` helper).

### Compare the two builds

To compare the profiling results and see how CPU time is distributed per
function, run:

```bash
amixis compare 2__2__2..xmltest.scriptout 1__1__1..xmltest.scriptout --max-rows 20
```

Amphimixis prints one cross-table per `perf` event. Each table shows, for every
function (symbol), the share of samples it accounts for in each build and the
difference between them. The two builds that are compared come from the order
of the arguments: the first file is **Build A** and the second is **Build B**.

### Reading the cross-table

Below is the comparison output converted from the console for readability. In
this run Build A (`2_2_2`) is the RISC-V build and Build B (`1_1_1`) is the
x86 build. A **positive Delta** means the function takes a larger share of
the event in the x86 build; a **negative Delta** means it takes a larger share
in the RISC-V build.

#### EVENT: BRANCH-MISSES

| Symbol | 2_2_2 (RISC-V) % | 1_1_1 (x86) % | Delta % |
| --- | ---: | ---: | ---: |
| `__strncmp_evex` | 0.00 | 32.97 | +32.97 |
| `[unknown]` | 35.59 | 6.42 | -29.17 |
| `strncmp` | 25.75 | 0.00 | -25.75 |
| `tinyxml2::StrPair::ParseText(char*, char const*, int, int*)` | 8.62 | 25.64 | +17.02 |
| `strncmp@plt` | 0.00 | 9.72 | +9.72 |
| `tinyxml2::XMLNode::DeleteNode(tinyxml2::XMLNode*)` | 0.00 | 6.38 | +6.38 |
| `__tunable_get_val` | 4.67 | 0.00 | -4.67 |
| `tinyxml2::XMLDocument::Identify(char*, tinyxml2::XMLNode**, bool)` | 3.73 | 0.00 | -3.73 |
| `tinyxml2::XMLText::~XMLText()` | 0.00 | 3.26 | +3.26 |
| `tinyxml2::MemPoolT<112ul>::SetTracked()` | 0.00 | 3.22 | +3.22 |
| `isalpha` | 0.00 | 3.21 | +3.21 |
| `unlink_chunk.isra.0` | 0.00 | 3.14 | +3.14 |
| `tinyxml2::XMLNode::ToDocument()` | 0.00 | 2.91 | +2.91 |
| `tinyxml2::XMLPrinter::PrintString(char const*, bool) [clone .part.0]` | 2.87 | 0.00 | -2.87 |
| `tinyxml2::XMLDocument::MarkInUse(tinyxml2::XMLNode const*)` | 2.83 | 0.00 | -2.83 |
| `strlen` | 2.61 | 0.00 | -2.61 |
| `tinyxml2::XMLElement::ParseDeep(char*, tinyxml2::StrPair*, int*)` | 2.56 | 0.00 | -2.56 |
| `tinyxml2::XMLNode::FirstChildElement(char const*) const` | 1.98 | 0.00 | -1.98 |
| `tinyxml2::StrPair::ParseName(char*)` | 1.46 | 0.00 | -1.46 |
| `tinyxml2::XMLNode::InsertEndChild(tinyxml2::XMLNode*) [clone .part.0]` | 0.88 | 0.00 | -0.88 |

The branch-miss profile clearly differs between the two platforms:

- x86 uses glibc's vectorized `__strncmp_evex` (AVX-512 EVEX encoding), which
  alone accounts for **32.97%** of branch misses — this function does not
  exist on RISC-V and does not appear in the RISC-V build at all.
- On RISC-V, the same work falls on the scalar glibc `strncmp` (**25.75%**)
  and on unresolved samples marked `[unknown]` (**35.59%**).
- The parsing hot spot `tinyxml2::StrPair::ParseText` is a significant source
  of branch misses on x86 (25.64%) but much less so on RISC-V (8.62%).

#### EVENT: CACHE-MISSES

| Symbol | 2_2_2 (RISC-V) % | 1_1_1 (x86) % | Delta % |
| --- | ---: | ---: | ---: |
| `[unknown]` | 0.00 | 57.89 | +57.89 |
| `tinyxml2::XMLNode::~XMLNode()` | 0.00 | 9.04 | +9.04 |
| `cfree@GLIBC_2.2.5` | 0.00 | 7.23 | +7.23 |
| `tinyxml2::MemPoolT<104ul>::Free(void*)` | 0.00 | 5.18 | +5.18 |
| `tinyxml2::XMLNode::InsertEndChild(tinyxml2::XMLNode*) [clone .part.0]` | 0.00 | 4.85 | +4.85 |
| `tinyxml2::XMLDocument::ToDocument()` | 0.00 | 4.75 | +4.75 |
| `tinyxml2::XMLDocument::Clear()` | 0.00 | 4.51 | +4.51 |
| `tinyxml2::StrPair::ParseText(char*, char const*, int, int*)` | 0.00 | 2.89 | +2.89 |
| `__memmove_evex_unaligned_erms` | 0.00 | 2.75 | +2.75 |
| `__printf_fp_l_buffer` | 0.00 | 0.91 | +0.91 |

> The zeros in the RISC-V column do **not** mean the RISC-V build produced no
> cache misses. The RISC-V kernel/hardware does not expose the `cache-misses`
> `perf` event under the same name, so Amphimixis had nothing to sample for it.
> The Delta column highlights only differences that appear in both builds, so
> events that are not available on one platform are simply reported as zero.

#### EVENT: CYCLES

| Symbol | 2_2_2 (RISC-V) % | 1_1_1 (x86) % | Delta % |
| --- | ---: | ---: | ---: |
| `tinyxml2::StrPair::ParseText(char*, char const*, int, int*)` | 6.86 | 16.43 | +9.56 |
| `tinyxml2::XMLDocument::Identify(char*, tinyxml2::XMLNode**, bool)` | 12.25 | 3.27 | -8.99 |
| `__strncmp_evex` | 0.00 | 8.32 | +8.32 |
| `strncmp` | 7.35 | 0.00 | -7.35 |
| `_int_malloc` | 0.00 | 6.69 | +6.69 |
| `tinyxml2::XMLNode::DeleteNode(tinyxml2::XMLNode*)` | 6.37 | 0.00 | -6.37 |
| `tinyxml2::XMLNode::~XMLNode()` | 4.90 | 0.00 | -4.90 |
| `tinyxml2::XMLElement::~XMLElement()` | 4.41 | 0.00 | -4.41 |
| `tinyxml2::XMLElement::ParseAttributes(char*, int*)` | 3.43 | 0.00 | -3.43 |
| `tinyxml2::XMLNode::ParseDeep(char*, tinyxml2::StrPair*, int*)` | 8.82 | 11.53 | +2.71 |
| `isspace` | 2.45 | 4.94 | +2.48 |
| `[unknown]` | 19.61 | 21.93 | +2.33 |
| `strlen` | 1.96 | 0.00 | -1.96 |
| `isalpha` | 3.43 | 1.53 | -1.90 |
| `tinyxml2::XMLNode::ToDocument()` | 0.00 | 1.74 | +1.74 |
| `_IO_file_xsputn@@GLIBC_2.2.5` | 0.00 | 1.71 | +1.71 |
| `__syscall_cancel` | 0.00 | 1.66 | +1.66 |
| `isalpha@plt` | 0.00 | 1.66 | +1.66 |
| `__vfprintf_internal` | 0.00 | 1.64 | +1.64 |
| `strncmp@plt` | 0.00 | 1.63 | +1.63 |

The cycle profile tells a similar story:

- `tinyxml2::XMLDocument::Identify` — an XML node-type identification routine
  that scans and compares strings — grows from **3.27%** of cycles on x86 to
  **12.25%** on RISC-V. It relies on `strncmp`, and without the vectorized
  x86 implementation this routine becomes one of the hottest spots on RISC-V.
- `strncmp` itself appears only in the RISC-V build (7.35%), confirming that
  string comparison is a migration cost driver.
- Several memory-management symbols (`_int_malloc`, destructors, `DeleteNode`)
  show exclusively on x86, while node-parsing and attribute routines become
  relatively more visible on RISC-V.

### What to do next

The cross-table pinpoints where the port loses performance. Common next steps,
described in the [Migration Readiness Methodology](migration_readiness_methodology.md):

- try compiler vectorization flags (`-ftree-vectorize` for GCC/Clang) and a
  newer RISC-V toolchain with a vector-capable `strncmp` or `memcpy`;
- build with LTO to help the compiler inline and optimize hot routines like
  `XMLDocument::Identify` and `StrPair::ParseText`;
- investigate the unresolved `[unknown]` samples — they often indicate missing
  debug info or kernel/dynamic-loader activity during profiling.

For details on every command used in this example, see the
[Usage Guide](usage_guide.md). If the RISC-V machine does not support a `perf`
event you need, see [Troubleshooting](troubleshooting.md).
