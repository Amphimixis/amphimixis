# \<Project Name> — Migration Readiness Report

**Analysis Date**: \<date>

**Target Architecture**: \<arch, e.g., RISC-V rv64gc>

**Reference Architecture**: \<x86_64 (Intel/AMD)>

**Analyst Agent**: amphimixis-orchestrator

---

## 1. Repository & Project Status

| Metric                    | Value                                                      |
|---------------------------|------------------------------------------------------------|
| **Repository**            | \<url>                                                      |
| **Latest Commit**         | \<date> (\<N> days ago)                                      |
| **Total Commits**         | \<N>                                                        |
| **Latest Tag**            | \<tag>                                                      |
| **Activity**              | \<actively maintained / sporadically maintained / archived> |
| **Build Systems**         | \<CMake / Makefile / Meson / ...>                           |
| **Test Count**            | \<N>                                                        |
| **External Dependencies** | \<count> — \<list>                                           |

### Distro Packages

\<available in Debian / Arch / Yocto / ...>

---

## 2. Platform-Specific Code Analysis

### Architecture Macros Found

| Macro        | File   | Line   | Scope of Guarded Code                   |
|--------------|--------|--------|-----------------------------------------|
| \<`_MSC_VER`> | \<file> | \<line> | \<just an #include / critical algorithm> |

### Platform Preprocessor Guards

| #ifdef        | Platform | What It Guards     |
|---------------|----------|--------------------|
| \<`__APPLE__`> | \<macOS>  | \<file I/O variant> |

### Portability Verdict

- **No exceptions**:
- **Alignment safe**:
- **Embedded usability**:
- **Overall**: \<N concerns found — list them>

---

## 3. Build & Test Results

| Platform                                     | Build | Tests Passed | Tests Failed | Notes                                   |
|----------------------------------------------|:-----:|:------------:|:------------:|-----------------------------------------|
| **\<reference x86>** (`-O3 -march=native -g`) | ✅    | \<N>          | \<M>          | \<flags>                                 |
| **\<target>** (`\<flags>`)                     | ✅/❌ | \<N>          | \<M>          | \<cross-compilation / remote / emulator> |

### Build Failures / Test Failures Detail

\<if any failures, describe root cause>

---

## 4. Performance Comparison

**IMPORTANT**: Don’t think, say the gist, if you don’t know, don’t write

### Experimental Conditions

- **CPU**: \<x86 model> vs \<target model>
- **Cores pinned**: \<list>
- **Warmup runs**: \<N>
- **Measurement runs**: \<N>

### Key Metrics

| Metric                    | x86  | \<target> | Ratio |
|---------------------------|:----:|:--------:|:-----:|
| Elapsed time (avg)        | \<μs> | \<μs>     | \<N>   |
| Instructions per cycle    | \<N>  | \<N>      | \<N>   |
| L1-dcache miss rate       | \<%>  | \<%>      | \<N>   |
| LLC miss rate             | \<%>  | \<%>      | \<N>   |
| Branch misprediction rate | \<%>  | \<%>      | \<N>   |
| Frontend Bound            | \<%>  | \<%>      | \<N>   |
| Backend Bound             | \<%>  | \<%>      | \<N>   |
| Retiring                  | \<%>  | \<%>      | \<N>   |

### Hotspot Analysis (x86)

| % Time | Function | Module | Analysis |
|:------:|----------|--------|----------|

### Hotspot Analysis (\<target>)

| % Time | Function | Module | Analysis |
|:------:|----------|--------|----------|

### Bottleneck Summary

\<Identify the top 1-3 bottlenecks with causal explanations>

- \<#1: function X accounts for N% of samples because ...>
- \<#2: high LLC miss rate suggests ...>

### Vectorization Intrinsics

- **Hand-written**: \<count> — \<list of intrinsics by ISA>
- **Compiler auto-generated**: \<found in binary / none>
- **Portability concern**: \<yes/no — explanation>

---

## 5. Optimization Results

### Vector Instructions in Binary

| Architecture    | Count | ISAs Found              |
|-----------------|:-----:|-------------------------|
| \<reference x86> | \<N>   | \<SSE/AVX/AVX-512/NEON*> |
| \<target>        | \<N>   | \<RVV/NEON/none>         |

\* *Note: NEON should not appear in an x86 binary — if it does, the analysis tool has a false positive.*

### Optimization Attempts

| #   | Optimization  | Before (ms) | After (ms) | Δ   | Causal Analysis |
|:---:|---------------|:-----------:|:----------:|:---:|-----------------|
| 1   | `\<flag>`      | \<N>         | \<N>        | ±X% | \<explanation>   |
| 2   | `\<allocator>` | \<N>         | \<N>        | ±X% | \<explanation>   |
| 3   | LTO           | \<N>         | \<N>        | ±X% | \<explanation>   |

### Recommended Optimizations

| Priority | Optimization | Expected Gain | Effort | Notes       |
|:--------:|--------------|:-------------:|:------:|-------------|
| 1        | \<name>       | \<X%>          | Low    | \<rationale> |
| 2        | \<name>       | \<X%>          | Medium | \<rationale> |
| 3        | \<name>       | \<X%>          | High   | \<rationale> |

---

## 6. Notes About Exploration process

<...>

---

## 7. Migration Readiness Summary

| Aspect                            | Status | Notes                                                         |
|-----------------------------------|--------|---------------------------------------------------------------|
| **Builds on \<reference x86>**     | ✅/❌ |                                                               |
| **Tests pass on \<reference x86>** | ✅/❌ |                                                               |
| **Builds on \<target>**            | ✅/❌ |                                                               |
| **Tests pass on \<target>**        | ✅/❌ |                                                               |
| **Zero external dependencies**    | ✅/❌ |                                                               |
| **No hand-written intrinsics**    | ✅/❌ |                                                               |
| **Alignment safe**                | ✅/❌ |                                                               |
| **Exceptions handled**            | ✅/⚠️ |                                                               |
| **Auto-vectorization**            | ✅/⚠️ | \<compiler generates vector code / no vectorization on target> |

### Migration Verdict

**\<READY / MINOR CONCERNS / NOT READY>** — \<one-sentence summary>

### Required Actions Before Migration

1. \<action item>
2. \<action item>
