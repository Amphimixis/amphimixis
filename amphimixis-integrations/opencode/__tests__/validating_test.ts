import { describe, expect, spyOn, test } from "bun:test";
import fs from "fs";
import { mkdir, unlink } from "fs/promises";
import path from "path";
import { chdir } from "process";
import yaml from "yaml";
import * as toolModule from "../tools/amphimixis-validate";

const amixis = [
  "uv", "run",
  "--project", path.join(__dirname, "../../.."),
  "python3", path.join(__dirname, "../../../amphimixis/amixis/__main__.py")
];
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
