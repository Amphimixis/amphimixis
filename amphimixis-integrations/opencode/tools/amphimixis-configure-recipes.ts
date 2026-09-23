import { tool } from "@opencode-ai/plugin";
import process from "process";
import fs from "fs";
import YAML from "yaml";
import path from "path";

function addIdField(objs: object[], startFrom: number = 1): void {
  let counter = startFrom;
  for (let i = 0; i < objs.length; ++i) {
    Reflect.defineProperty(objs[i], "id", { value: counter, enumerable: true });
    counter += 1;
  }
}

function sanitizeForYaml(obj: unknown): unknown {
  if (obj === null || obj === undefined) return obj;
  if (typeof obj !== "object") return obj;
  if (Array.isArray(obj)) return obj.map(sanitizeForYaml);
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    if (typeof value !== "function" && typeof value !== "symbol") {
      result[key] = sanitizeForYaml(value);
    }
  }
  return result;
}

function readExistingConfig(configPath: string): Record<string, unknown> {
  if (fs.existsSync(configPath)) {
    const content = fs.readFileSync(configPath, { encoding: "utf-8" });
    const parsed = YAML.parse(content);
    return parsed && typeof parsed === "object" ? parsed : {};
  }
  return {};
}

export default tool({
  description: `Add build recipes (configurations) to Amphimixis config. Also sets build_system and runner. Creates input.yml if absent, merges with existing config.

RULES:
- config_flags: REQUIRED. String of build configuration flags.
  Examples: '-DCMAKE_BUILD_TYPE=RelWithDebInfo', '-DCMAKE_BUILD_TYPE=Debug'
- build_system: Optional. Values: 'cmake', 'make'. Auto-detected if omitted.
- runner: Optional. Values: 'make', 'ninja'. Auto-detected based on build_system.
- jobs: Optional. Positive integer for parallel build jobs.
- sysroot: Optional. Absolute path for sysroot of toolchain.
- toolchain: Optional. Object with absolute paths to compilers and tools.
  Example: {c_compiler: '/usr/bin/gcc', cxx_compiler: '/usr/bin/g++'}
  Available toolchain keys: ar, as, ld, nm, objcopy, objdump, ranlib, readelf, strip,
    c_compiler, cxx_compiler, csharp_compiler, cuda_compiler, objc_compiler, objcxx_compiler,
    fortran_compiler, hip_compiler, ispc_compiler, swift_compiler, asm_compiler,
    asm_nasm_compiler, asm_marmasm_compiler, asm_masm_compiler, asm_att_compiler
- compiler_flags: Optional. Object with flags per language.
  Example: {c_flags: '-O2', cxx_flags: '-std=c++17'}
  Available flag keys: c_flags, cxx_flags, csharp_flags, cuda_flags, objc_flags, objcxx_flags,
    fortran_flags, hip_flags, ispc_flags, swift_flags, asm_flags, asm_nasm_flags,
    asm_marmasm_flags, asm_masm_flags, asm_att_flags

BEHAVIOR:
- Recipe IDs are auto-assigned sequentially (1, 2, 3...). The tool returns the mapping.
- build_system and runner OVERWRITE any previous values in the config.
- New recipes are APPENDED to existing ones.

EXAMPLES:
  Single release recipe with cmake:
    build_system: 'cmake'
    recipes: [{config_flags: '-DCMAKE_BUILD_TYPE=RelWithDebInfo'}]

  With toolchain and custom runner:
    build_system: 'cmake'
    runner: 'ninja'
    recipes: [{config_flags: '-DCMAKE_BUILD_TYPE=Debug', toolchain: {c_compiler: '/opt/gcc-riscv/bin/riscv64-linux-gnu-gcc'}}]

CALL THIS SECOND, after platforms, before builds.`,
  args: {
    configFilePath: tool.schema
      .string()
      .optional()
      .describe("Path to config file (default: input.yml in current directory)"),
    build_system: tool.schema
      .string()
      .optional()
      .describe("Build system name. Available values: cmake, make"),
    runner: tool.schema
      .string()
      .optional()
      .describe(
        "Low-level build (running) system name. Available values: make, ninja",
      ),
    recipes: tool.schema
      .array(
        tool.schema.object({
          config_flags: tool.schema
            .string()
            .describe("Build configuration flags (required)"),
          jobs: tool.schema
            .number()
            .int()
            .optional()
            .describe("Number of parallel build jobs"),
          toolchain: tool.schema
            .object({
              ar: tool.schema.string().optional().describe("Absolute path to ar (archive tool)"),
              as: tool.schema.string().optional().describe("Absolute path to as (assembler)"),
              ld: tool.schema.string().optional().describe("Absolute path to ld (linker)"),
              nm: tool.schema.string().optional().describe("Absolute path to nm (symbol tool)"),
              objcopy: tool.schema.string().optional().describe("Absolute path to objcopy"),
              objdump: tool.schema.string().optional().describe("Absolute path to objdump"),
              ranlib: tool.schema.string().optional().describe("Absolute path to ranlib"),
              readelf: tool.schema.string().optional().describe("Absolute path to readelf"),
              strip: tool.schema.string().optional().describe("Absolute path to strip"),
              c_compiler: tool.schema.string().optional().describe("Absolute path to C compiler"),
              cxx_compiler: tool.schema.string().optional().describe("Absolute path to C++ compiler"),
              csharp_compiler: tool.schema.string().optional().describe("Absolute path to C# compiler"),
              cuda_compiler: tool.schema.string().optional().describe("Absolute path to CUDA compiler"),
              objc_compiler: tool.schema.string().optional().describe("Absolute path to Objective-C compiler"),
              objcxx_compiler: tool.schema.string().optional().describe("Absolute path to Objective-C++ compiler"),
              fortran_compiler: tool.schema.string().optional().describe("Absolute path to Fortran compiler"),
              hip_compiler: tool.schema.string().optional().describe("Absolute path to HIP compiler"),
              ispc_compiler: tool.schema.string().optional().describe("Absolute path to ISPC compiler"),
              swift_compiler: tool.schema.string().optional().describe("Absolute path to Swift compiler"),
              asm_compiler: tool.schema.string().optional().describe("Absolute path to assembler"),
              asm_nasm_compiler: tool.schema.string().optional().describe("Absolute path to NASM"),
              asm_marmasm_compiler: tool.schema.string().optional().describe("Absolute path to MARMASM"),
              asm_masm_compiler: tool.schema.string().optional().describe("Absolute path to MASM"),
              asm_att_compiler: tool.schema.string().optional().describe("Absolute path to AT&T assembler"),
              c_flags: tool.schema.string().optional().describe("C compiler flags in toolchain"),
              cxx_flags: tool.schema.string().optional().describe("C++ compiler flags in toolchain"),
              csharp_flags: tool.schema.string().optional().describe("C# flags in toolchain"),
              cuda_flags: tool.schema.string().optional().describe("CUDA flags in toolchain"),
              objc_flags: tool.schema.string().optional().describe("Objective-C flags in toolchain"),
              objcxx_flags: tool.schema.string().optional().describe("Objective-C++ flags in toolchain"),
              fortran_flags: tool.schema.string().optional().describe("Fortran flags in toolchain"),
              hip_flags: tool.schema.string().optional().describe("HIP flags in toolchain"),
              ispc_flags: tool.schema.string().optional().describe("ISPC flags in toolchain"),
              swift_flags: tool.schema.string().optional().describe("Swift flags in toolchain"),
              asm_flags: tool.schema.string().optional().describe("Assembler flags in toolchain"),
              asm_nasm_flags: tool.schema.string().optional().describe("NASM flags in toolchain"),
              asm_marmasm_flags: tool.schema.string().optional().describe("MARMASM flags in toolchain"),
              asm_masm_flags: tool.schema.string().optional().describe("MASM flags in toolchain"),
              asm_att_flags: tool.schema.string().optional().describe("AT&T assembler flags in toolchain"),
            })
            .optional()
            .describe("Absolute paths to compilers/tools or flags for the toolchain"),
          compiler_flags: tool.schema
            .object({
              c_flags: tool.schema.string().optional().describe("C flags"),
              cxx_flags: tool.schema.string().optional().describe("C++ flags"),
              csharp_flags: tool.schema.string().optional().describe("C# flags"),
              cuda_flags: tool.schema.string().optional().describe("CUDA flags"),
              objc_flags: tool.schema.string().optional().describe("Objective-C flags"),
              objcxx_flags: tool.schema.string().optional().describe("Objective-C++ flags"),
              fortran_flags: tool.schema.string().optional().describe("Fortran flags"),
              hip_flags: tool.schema.string().optional().describe("HIP flags"),
              ispc_flags: tool.schema.string().optional().describe("ISPC flags"),
              swift_flags: tool.schema.string().optional().describe("Swift flags"),
              asm_flags: tool.schema.string().optional().describe("Assembler flags"),
              asm_nasm_flags: tool.schema.string().optional().describe("NASM flags"),
              asm_marmasm_flags: tool.schema.string().optional().describe("MARMASM flags"),
              asm_masm_flags: tool.schema.string().optional().describe("MASM flags"),
              asm_att_flags: tool.schema.string().optional().describe("AT&T assembler flags"),
            })
            .optional()
            .describe("List of flags for compilers"),
          sysroot: tool.schema
            .string()
            .optional()
            .describe("Absolute path to sysroot for toolchain"),
        }),
      )
      .describe("List of recipe configurations to add"),
  },
  async execute(args) {
    const configPath = args.configFilePath || path.join(process.cwd(), "input.yml");
    const config = readExistingConfig(configPath);

    if (args.build_system) {
      config.build_system = args.build_system;
    }
    if (args.runner) {
      config.runner = args.runner;
    }

    const existingRecipes = (config.recipes as object[]) || [];
    const maxId = existingRecipes.reduce(
      (max, r) => Math.max(max, (r as Record<string, unknown>).id as number || 0),
      0,
    );

    addIdField(args.recipes, maxId + 1);
    config.recipes = [...existingRecipes, ...args.recipes];

    const yamlContent = YAML.stringify(sanitizeForYaml(config));
    fs.writeFileSync(configPath, yamlContent, { encoding: "utf-8" });

    const summary: Record<string, unknown> = {};
    if (config.build_system) summary.build_system = config.build_system;
    if (config.runner) summary.runner = config.runner;
    const assignedIds = (config.recipes as Record<string, unknown>[])
      .slice(existingRecipes.length)
      .map((r) => ({ id: r.id, config_flags: r.config_flags }));
    summary.recipeIds = assignedIds;

    return `Recipes added to ${configPath}. Summary: ${JSON.stringify(summary)}`;
  },
});
