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
  description: `Add platforms (machines) to Amphimixis config. Creates input.yml if absent, merges with existing config.

RULES:
- arch: REQUIRED. One of: 'x86', 'riscv', 'arm'
- address: OMIT for LOCAL machine. REQUIRED for REMOTE (IP address or domain name).
- username: REQUIRED if address is set (remote machine). OMIT for local.
- password: Optional for remote. If omitted, SSH keys are used.
- port: Optional. Default: 22. Range: 1-65535.

BEHAVIOR:
- IDs are auto-assigned sequentially (1, 2, 3...). The tool returns the mapping.
- If input.yml already has platforms, new ones are appended with next available IDs.

EXAMPLES:
  Single local machine: [{arch: 'x86'}]
  Single remote machine: [{arch: 'riscv', address: '192.168.1.100', username: 'root'}]
  Two machines: [{arch: 'x86'}, {arch: 'riscv', address: '10.0.0.5', username: 'bianbu'}]

CALL THIS FIRST, before recipes and builds.`,
  args: {
    configFilePath: tool.schema
      .string()
      .optional()
      .describe("Path to config file (default: input.yml in current directory)"),
    platforms: tool.schema
      .array(
        tool.schema.object({
          arch: tool.schema
            .string()
            .describe(
              "Architecture of the machine. Available values: riscv, x86, arm",
            ),
          address: tool.schema
            .string()
            .optional()
            .describe(
              "IP address or domain name (OMIT for local machine, REQUIRED for remote)",
            ),
          username: tool.schema
            .string()
            .optional()
            .describe("SSH username (REQUIRED if address is set, OMIT for local)"),
          password: tool.schema
            .string()
            .optional()
            .describe(
              "SSH password (optional — use SSH keys via ssh-agent for better security)",
            ),
          port: tool.schema
            .number()
            .int()
            .optional()
            .describe("SSH port (default: 22, range: 1-65535)"),
        }),
      )
      .describe("List of platforms (machines) to add"),
  },
  async execute(args) {
    const configPath = args.configFilePath || path.join(process.cwd(), "input.yml");
    const config = readExistingConfig(configPath);

    const existingPlatforms = (config.platforms as object[]) || [];
    const maxId = existingPlatforms.reduce(
      (max, p) => Math.max(max, (p as Record<string, unknown>).id as number || 0),
      0,
    );

    addIdField(args.platforms, maxId + 1);
    config.platforms = [...existingPlatforms, ...args.platforms];

    const yamlContent = YAML.stringify(sanitizeForYaml(config));
    fs.writeFileSync(configPath, yamlContent, { encoding: "utf-8" });

    const assignedIds = (config.platforms as Record<string, unknown>[])
      .slice(existingPlatforms.length)
      .map((p) => ({ id: p.id, arch: p.arch }));
    return `Platforms added to ${configPath}. Assigned IDs: ${JSON.stringify(assignedIds)}`;
  },
});
