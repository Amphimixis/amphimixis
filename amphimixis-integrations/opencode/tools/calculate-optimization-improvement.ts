import { tool } from '@opencode-ai/plugin';
import fs from 'fs';

export default tool({
  description:
    'Calculate optimization improvement percentage.'
    + ' Formula: improvementPcnt = (optimizedValue / baselineValue) * 100',
  args: {
    baselineValue: tool.schema
      .number()
      .describe('Baseline measurement value (before optimization)'),
    optimizedValue: tool.schema
      .number()
      .describe('Optimized measurement value (after optimization)'),
    parameter: tool.schema
      .string()
      .describe('Measured parameter name (e.g. "real_time", "user_time", "IPC")'),
    measuredObject: tool.schema
      .string()
      .describe('Executable name the measurement belongs to'),
    baselineBuild: tool.schema
      .string()
      .describe('Build name for the baseline measurement'),
    optimizedBuild: tool.schema
      .string()
      .describe('Build name for the optimized measurement'),
  },
  async execute(args) {
    const fileName = 'improvements.json';
    const improvementPcnt = (args.optimizedValue / args.baselineValue) * 100;
    let data;
    try {
      data = JSON.parse(fs.readFileSync(fileName, 'utf-8'));
    } catch {
      // If the file doesn't exist or is not valid JSON, create a new object
      data = [];
    }

    data.push(
      {
        parameter: args.parameter,
        measuredObject: args.measuredObject,
        baselineBuild: args.baselineBuild,
        optimizedBuild: args.optimizedBuild,
        baselineValue: args.baselineValue,
        optimizedValue: args.optimizedValue,
        improvementPcnt: Math.round(improvementPcnt * 100) / 100, // Round to 2 decimal places
      },
    );

    await Bun.write(fileName, JSON.stringify(data, null, 2));

    return `Improvement: ${improvementPcnt.toFixed(2)}%`;
  },
});
