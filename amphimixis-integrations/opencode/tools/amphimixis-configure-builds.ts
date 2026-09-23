import { tool } from "@opencode-ai/plugin";
import process from "process";
import fs from "fs";
import YAML from "yaml";
import path from "path";

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

export default tool({
  description: `Add builds (links between platforms and recipes) to Amphimixis config.
REQUIRES existing input.yml with platforms and recipes already configured.

IMPORTANT: Read the input.yml FIRST with 'read' tool to see auto-assigned platform and recipe IDs.

RULES:
- build_machine: REQUIRED. Must match a platform ID from configure-platforms step.
- run_machine: REQUIRED. Must match a platform ID from configure-platforms step.
  Can be same as or different from build_machine.
- recipe_id: REQUIRED. Must match a recipe ID from configure-recipes step.
- executables: Optional. List of relative paths from build directory.
  Example: ['bin/my_app', 'tests/benchmark']
  If omitted, profiles first executable found in build directory.

VALIDATION: Each build_machine, run_machine, and recipe_id is validated against existing config.
On error, returns list of valid IDs for self-correction. No changes are written until all errors are fixed.

EXAMPLES (assuming platform IDs [1, 2] and recipe ID [1]):
  Build and run on same machine: [{build_machine: 1, run_machine: 1, recipe_id: 1}]
  Cross build (x86->riscv): [{build_machine: 1, run_machine: 2, recipe_id: 1}]
  With executables: [{build_machine: 1, run_machine: 1, recipe_id: 1, executables: ['bin/app']}]

CALL THIS LAST, after platforms and recipes are configured.`,
  args: {
    configFilePath: tool.schema
      .string()
      .describe("Path to existing config file (input.yml) with platforms and recipes"),
    builds: tool.schema
      .array(
        tool.schema.object({
          build_machine: tool.schema
            .number()
            .int()
            .describe(
              "Platform ID where to build. Must match an existing platform ID.",
            ),
          run_machine: tool.schema
            .number()
            .int()
            .describe(
              "Platform ID where to run/profile. Must match an existing platform ID.",
            ),
          recipe_id: tool.schema
            .number()
            .int()
            .describe(
              "Recipe ID to use for this build. Must match an existing recipe ID.",
            ),
          executables: tool.schema
            .string()
            .array()
            .optional()
            .describe(
              "List of relative paths to executables to profile (from build dir)",
            ),
        }),
      )
      .describe("List of build configurations to add"),
  },
  async execute(args) {
    const configPath = args.configFilePath || path.join(process.cwd(), "input.yml");

    if (!fs.existsSync(configPath)) {
      return `Error: Config file not found at ${configPath}. Configure platforms and recipes first before adding builds.`;
    }

    const content = fs.readFileSync(configPath, { encoding: "utf-8" });
    const config = (YAML.parse(content) as Record<string, unknown>) || {};

    const platforms = (config.platforms || []) as Record<string, unknown>[];
    const recipes = (config.recipes || []) as Record<string, unknown>[];

    const platformIds = platforms.map((p) => p.id);
    const recipeIds = recipes.map((r) => r.id);

    const errors: string[] = [];
    for (let i = 0; i < args.builds.length; i++) {
      const build = args.builds[i];
      if (!platformIds.includes(build.build_machine)) {
        errors.push(
          `Build #${i + 1}: build_machine=${build.build_machine} not found. Valid platform IDs: [${platformIds.join(", ")}]`,
        );
      }
      if (!platformIds.includes(build.run_machine)) {
        errors.push(
          `Build #${i + 1}: run_machine=${build.run_machine} not found. Valid platform IDs: [${platformIds.join(", ")}]`,
        );
      }
      if (!recipeIds.includes(build.recipe_id)) {
        errors.push(
          `Build #${i + 1}: recipe_id=${build.recipe_id} not found. Valid recipe IDs: [${recipeIds.join(", ")}]`,
        );
      }
    }

    if (errors.length > 0) {
      return `Validation failed. No changes written.\n${errors.join("\n")}\nFix the errors and retry.`;
    }

    const existingBuilds = (config.builds as object[]) || [];
    config.builds = [...existingBuilds, ...args.builds];

    const yamlContent = YAML.stringify(sanitizeForYaml(config));
    fs.writeFileSync(configPath, yamlContent, { encoding: "utf-8" });

    const buildSummary = args.builds.map((b: Record<string, unknown>) => ({
      build_machine: b.build_machine,
      run_machine: b.run_machine,
      recipe_id: b.recipe_id,
      executables: b.executables || "(auto-detect)",
    }));

    return `Builds added to ${configPath}. ${buildSummary.length} build(s) configured: ${JSON.stringify(buildSummary)}`;
  },
});
