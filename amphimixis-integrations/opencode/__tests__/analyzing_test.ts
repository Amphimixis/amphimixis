import {mkdir, writeFile} from 'fs/promises';
import {chdir} from 'process';
import {test, expect, describe, spyOn} from 'bun:test';
import path from 'path';
import * as toolModule from '../tools/amphimixis-analyze';

const amixis = path.join(__dirname, "../../../.venv/bin/amixis");
spyOn(toolModule, "amixis").mockReturnValue(amixis);
console.log(amixis);

describe('Analyzing tool', () => {
  test('analyzing function', async () => {
    const tmpDirPath = '/tmp/amphimixis/tests/opencode/analyze';
    await mkdir(tmpDirPath, {recursive: true});
    chdir(tmpDirPath);
    const tmpProjPath = path.join(tmpDirPath, 'proj');
    await mkdir(tmpDirPath, {recursive: true});
    await mkdir(tmpProjPath, {recursive: true});
    const testsPath = path.join(tmpProjPath, 'tests');
    const makefilePath = path.join(tmpProjPath, 'Makefile');
    await mkdir(testsPath, {recursive: true});
    await writeFile(makefilePath, 'all:\n\techo hello');
    // @ts-ignore
    const output = await toolModule.default.execute({projectPath: tmpProjPath});
    expect(output.toString().length).toBeGreaterThan(0);
  });
});
