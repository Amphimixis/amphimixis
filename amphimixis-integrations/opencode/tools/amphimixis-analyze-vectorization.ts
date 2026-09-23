import { tool } from "@opencode-ai/plugin";

export const amixis = () => '$AMIXIS_PATH';

export default tool({
  description: `Use objdump to analyze a built binary for platform-specific vector instructions.
Helps determine if the compiler auto-vectorized code or if manual intrinsics were used.

RULES:
- binaryPath: REQUIRED. Path to the built executable or object file.
- arch: REQUIRED. Target architecture (x86, arm, riscv).
  If omitted, attempts to auto-detect from the binary.
- Returns count and listing of vector instructions found.

EXAMPLES:
  {binaryPath: './build/bin/my_app', arch: 'riscv'}
  {binaryPath: './build/bin/benchmark', arch: 'x86'}`,
  args: {
    binaryPath: tool.schema
      .string()
      .describe("Path to the built executable or object file"),
    arch: tool.schema
      .string()
      .describe("Target architecture (x86, avx, avx512, neon, rvv)"),
  },
  async execute(args) {
    const cmd = [amixis(), 'analyze', '-v', args.arch, args.binaryPath];
    return (await Bun.$`${cmd}`.text()).trim();
  },
});
