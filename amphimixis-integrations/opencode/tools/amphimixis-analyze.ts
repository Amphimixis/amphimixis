import { tool } from '@opencode-ai/plugin';
import path from 'node:path';

export const amixis = () => '$AMIXIS_PATH';

export default tool({
  description:
    'Analyze project repository: find CI, tests, benchmarks, dependencies, documentation, build systems',
  args: {
    projectPath: tool.schema
      .string()
      .describe('Path to repository of analyzing project'),
  },
  async execute(args) {
    const projectDir = `./${path.basename(args.projectPath)}`;
    const cmd = [amixis(), 'analyze', args.projectPath];
    return (await Bun.$.cwd(projectDir)`${cmd}`.text()).trim();
  },
});