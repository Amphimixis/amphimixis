import { describe, expect, test } from 'bun:test';
import { mkdir, rm, writeFile } from 'fs/promises';
import InspectorGeneral from 'inspector_general';
import path from 'path';
import { chdir } from 'process';

const TESTS_DIR = '/tmp/amphimixis/tests/opencode/inspector';

const CT_TABLE = [
  '| Symbol | ref % | opt % | Delta % |',
  '| --- | --- | --- | --- |',
  '| main | 10 | 12 | 2 |',
].join('\n');

const IMPROVEMENTS_TABLE = [
  '| Measured | Baseline value | Optimized value | Improvement % |',
  '| --- | --- | --- | --- |',
  '| runtime | 10 | 12 | 120 |',
].join('\n');

const REPORT = [
  '# Amphimixis TinyXML2 report',
  '',
  '## Cross-table',
  CT_TABLE,
  '',
  '## Improvement of opt compared to base',
  IMPROVEMENTS_TABLE,
  '',
].join('\n');

const IMPROVEMENTS_JSON = JSON.stringify([{
  parameter: 'runtime',
  measuredObject: 'runtime',
  baselineBuild: 'opt',
  optimizedBuild: 'base',
  baselineValue: 10,
  optimizedValue: 12,
  improvementPcnt: 120,
}]);

async function prepareCase(name: string, files: Record<string, string>): Promise<void> {
  const dir = path.join(TESTS_DIR, name);
  await rm(dir, { recursive: true, force: true });
  await mkdir(dir, { recursive: true });
  chdir(dir);
  for (const [fileName, content] of Object.entries(files)) {
    const filePath = path.join(dir, fileName);
    await mkdir(path.dirname(filePath), { recursive: true });
    await writeFile(filePath, content);
  }
}

function joinOutput(output: string[]): string {
  return output.join('\n');
}

describe('Inspector InspectorGeneral.inspect()', () => {
  test('reports all missing required steps when no files are present', async () => {
    await prepareCase('empty', {});
    const output = joinOutput(InspectorGeneral.inspect()[1]);

    expect(output).toContain('## Missing required steps');
    expect(output).toContain('- using `amphimixis-compare` tool to');
    expect(output).toContain('- using `calculate-optimization-improvement`');
    expect(output).toContain('- FATAL: no report file found, please');
    expect(output).toContain('**IMPRORTANT**');
  });

  test('marks missing steps without the fatal report message when only the report exists', async () => {
    await prepareCase('report-only', { 'amphimixis-tinyxml2-report.md': REPORT });
    const output = joinOutput(InspectorGeneral.inspect()[1]);

    expect(output).toContain('## Missing required steps');
    expect(output).not.toContain('- FATAL: no report file found, please');
    expect(output).not.toBe('');
  });

  test('accepts correct cross-table and improvements data', async () => {
    await prepareCase('correct', {
      'stats.json': '{}',
      'cross-tables/CT-ref-opt.md': CT_TABLE,
      'improvements.json': IMPROVEMENTS_JSON,
      'amphimixis-tinyxml2-report.md': REPORT,
    });
    const output = joinOutput(InspectorGeneral.inspect()[1]);

    expect(output).toContain('## Cross-table inspection results');
    expect(output).toContain('- All fine.');
    expect(output).toContain('## Improvements table inspection results');
  });

  test('rejects a cross-table that differs from the CT file', async () => {
    const wrongReport = REPORT.replace('| main | 10 | 12 | 2 |', '| main | 10 | 12 | 5 |');
    await prepareCase('wrong-cross-table', {
      'stats.json': '{}',
      'cross-tables/CT-ref-opt.md': CT_TABLE,
      'improvements.json': IMPROVEMENTS_JSON,
      'amphimixis-tinyxml2-report.md': wrongReport,
    });
    const output = joinOutput(InspectorGeneral.inspect()[1]);

    expect(output).toContain('- Table incorrect, read the "CT-<...>.md" files again');
  });

  test('rejects an improvements table that differs from improvements.json', async () => {
    const wrongReport = REPORT.replace('| runtime | 10 | 12 | 120 |', '| runtime | 11 | 12 | 120 |');
    await prepareCase('wrong-improvements', {
      'stats.json': '{}',
      'cross-tables/CT-ref-opt.md': CT_TABLE,
      'improvements.json': IMPROVEMENTS_JSON,
      'amphimixis-tinyxml2-report.md': wrongReport,
    });
    const output = joinOutput(InspectorGeneral.inspect()[1]);

    expect(output).toContain('- Improvements table contains incorrect data, read the');
  });
});

// eslint-disable-next-line no-unused-vars -- function type parameter is positional
type EventHandler = (args: { event: Record<string, unknown> }) => Promise<unknown>;

function makeClient() {
  const prompts: string[] = [];
  const client = {
    app: {
      log: async () => {},
    },
    session: {
      prompt: async (args: { body: { parts: Array<{ text: string }> } }) => {
        prompts.push(args.body.parts[0].text);
      },
    },
  };
  return { client, prompts };
}

async function makeEmitter(client: { session: { prompt: Function } }) {
  const plugin = await (await import('../plugins/amphimixis-inspector')).default({ client } as never);
  return (plugin as { event: EventHandler }).event;
}

describe('Inspector plugin events', () => {
  test('does not nag when the completion marker is present', async () => {
    const { client, prompts } = makeClient();
    const emit = await makeEmitter(client);

    const textPart = (text: string) => ({
      type: 'message.part.updated',
      properties: { part: { type: 'text', text, sessionID: 'ses_1' } },
    });
    const stepFinishPart = {
      type: 'message.part.updated',
      properties: { part: { type: 'step-finish', sessionID: 'ses_1' } },
    };

    await emit({ event: stepFinishPart });
    expect(prompts.length).toBe(0);

    await emit({ event: textPart('still working on the report') });
    await emit({ event: stepFinishPart });
    expect(prompts.length).toBe(0);
  });
});
