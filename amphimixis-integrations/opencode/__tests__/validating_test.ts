import fs from "fs";
import path from "path";
import { chdir } from "process";
import { unlink, mkdir } from "fs/promises";
import yaml from "yaml";
import { test, expect, describe, spyOn } from "bun:test";
import * as toolModule from "../tools/amphimixis-validate";

const amixis = path.join(__dirname, "../../../.venv/bin/amixis");
spyOn(toolModule, "amixis").mockReturnValue(amixis);

describe("Validating config file tool", () => {
  test("validating function", async () => {
    const tmpDirPath = "/tmp/amphimixis/tests/opencode/validate";
    const tmpConfigPath = path.join(tmpDirPath, "input.yml");
    try {
      await unlink(tmpConfigPath);
    } catch {
      /* empty */
    }
    await mkdir(tmpDirPath, { recursive: true });
    chdir(tmpDirPath);
    const BUILD_SYSTEM = "cmake";
    const RUNNER = "ninja";
    const ARCH = "riscv";
    const CONFIG_FLAGS = "-DCMAKE_BUILD_TYPE=RelWithDebInfo";
    fs.writeFileSync(
      tmpConfigPath,
      yaml.stringify({
        build_system: BUILD_SYSTEM,
        runner: RUNNER,
        platforms: [
          {
            id: 1,
            arch: ARCH,
          },
          {
            id: 2,
            arch: ARCH,
          },
        ],
        recipes: [
          {
            id: 1,
            config_flags: CONFIG_FLAGS,
          },
        ],
        builds: [
          {
            build_machine: 1,
            run_machine: 2,
            recipe_id: 1,
          },
        ],
      }),
    );
    // @ts-ignore
    const output = await toolModule.default.execute({ configFilePath: tmpConfigPath });
    expect(output.toString().includes("is correct")).toBe(true);
  });
});
