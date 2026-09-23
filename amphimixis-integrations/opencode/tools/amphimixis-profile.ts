import { tool } from '@opencode-ai/plugin';
import path from 'node:path';

export const amixis = () => '$AMIXIS_PATH';

export default tool({
  description:
    'Profile project executables with time, perf-stat and perf-record',
  args: {
    project_path: tool.schema
      .string()
      .describe('Path to repository of building project'),
    config: tool.schema
      .string()
      .optional()
      .describe(
        'Path to config file. If not specified, checks for input.yml in current directory or automatically create it',
      ),
    build_name: tool.schema
      .string()
      .optional()
      .describe(
        'Name of specific build from input.yml to profile (e.g. "1_2_1")',
      ),
  },
  async execute(args) {
    const projectDir = `./${path.basename(args.project_path)}`;
    const cmd = [amixis(), 'profile', args.project_path];
    if (args.config) cmd.push(`--config=${args.config}`);
    if (args.build_name) cmd.push(`--build-name=${args.build_name}`);

    const result = await Bun.$.cwd(projectDir)`${cmd}`.text();
    return result.trim();
  },
});