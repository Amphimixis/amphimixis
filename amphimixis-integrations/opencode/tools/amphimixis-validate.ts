import {tool} from '@opencode-ai/plugin';

export const amixis = () => '$AMIXIS_PATH';

export default tool({
  description: 'Check the Amphimixis configuration file for correctness',
  args: {
    configFilePath: tool.schema
        .string()
        .describe(
            'The path to the configuration file for validation (path to `input.yml`)',
        ),
  },
  async execute(args) {
    const cmd = [amixis(), 'validate', args.configFilePath];
    return (await Bun.$`${cmd}`.text()).trim();
  },
});
