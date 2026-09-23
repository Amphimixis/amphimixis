import fs from "fs";
import { unlink, mkdir } from "fs/promises";
import yaml from "yaml";
import { test, expect, describe } from "bun:test";
import path from "path";
import { chdir } from "process";

const tmpDirPath = "/tmp/amphimixis/tests/opencode/configure";
const tmpConfigPath = path.join(tmpDirPath, "input.yml");
const platformConfiguringToolModulePath = "../tools/amphimixis-configure-platforms.ts";
const recipeConfiguringToolModulePath = "../tools/amphimixis-configure-recipes.ts";
const buildConfiguringToolModulePath = "../tools/amphimixis-configure-builds.ts";

describe("Configuring tool", () => {
  test("configure-platforms creates file with auto-assigned IDs", async () => {
    try {
      await unlink(tmpConfigPath);
    } catch {
      /* empty */
    }
    await mkdir(tmpDirPath, { recursive: true });
    chdir(tmpDirPath);

    const toolModule = await import(platformConfiguringToolModulePath);
    const tool = toolModule.default;

    const output = await tool.execute({
      configFilePath: tmpConfigPath,
      platforms: [{ arch: "x86" }, { arch: "riscv" }],
    });

    const result = yaml.parse(
      fs.readFileSync(tmpConfigPath, { encoding: "utf-8", flag: "r" }),
    ) as {
      platforms: Array<{ id: number; arch: string }>;
    };

    expect(result.platforms).toHaveLength(2);
    expect(result.platforms[0].id).toBe(1);
    expect(result.platforms[0].arch).toBe("x86");
    expect(result.platforms[1].id).toBe(2);
    expect(result.platforms[1].arch).toBe("riscv");
    expect(output).toContain("Assigned IDs");
  });

  test("configure-platforms appends to existing platforms", async () => {
    await mkdir(tmpDirPath, { recursive: true });
    chdir(tmpDirPath);

    const toolModule = await import(platformConfiguringToolModulePath);
    const tool = toolModule.default;

    await tool.execute({
      configFilePath: tmpConfigPath,
      platforms: [{ arch: "arm" }],
    });

    const result = yaml.parse(
      fs.readFileSync(tmpConfigPath, { encoding: "utf-8", flag: "r" }),
    ) as {
      platforms: Array<{ id: number; arch: string }>;
    };

    expect(result.platforms).toHaveLength(3);
    expect(result.platforms[2].id).toBe(3);
    expect(result.platforms[2].arch).toBe("arm");
  });

  test("configure-recipes adds recipes and build_system", async () => {
    chdir(tmpDirPath);

    const toolModule = await import(recipeConfiguringToolModulePath);
    const tool = toolModule.default;

    const output = await tool.execute({
      configFilePath: tmpConfigPath,
      build_system: "cmake",
      runner: "ninja",
      recipes: [
        { config_flags: "-DCMAKE_BUILD_TYPE=RelWithDebInfo" },
        { config_flags: "-DCMAKE_BUILD_TYPE=Debug" },
      ],
    });

    const result = yaml.parse(
      fs.readFileSync(tmpConfigPath, { encoding: "utf-8", flag: "r" }),
    ) as {
      build_system: string;
      runner: string;
      recipes: Array<{ id: number; config_flags: string }>;
      platforms: Array<{ id: number; arch: string }>;
    };

    expect(result.build_system).toBe("cmake");
    expect(result.runner).toBe("ninja");
    expect(result.recipes).toHaveLength(2);
    expect(result.recipes[0].id).toBe(1);
    expect(result.recipes[0].config_flags).toBe("-DCMAKE_BUILD_TYPE=RelWithDebInfo");
    expect(result.recipes[1].id).toBe(2);
    expect(result.platforms).toHaveLength(3); // preserved from previous tests
    expect(output).toContain("Recipes added");
  });

  test("configure-builds validates and adds builds", async () => {
    chdir(tmpDirPath);

    const toolModule = await import(buildConfiguringToolModulePath);
    const tool = toolModule.default;

    const output = await tool.execute({
      configFilePath: tmpConfigPath,
      builds: [
        { build_machine: 1, run_machine: 1, recipe_id: 1 },
        { build_machine: 2, run_machine: 2, recipe_id: 2, executables: ["bin/app"] },
      ],
    });

    const result = yaml.parse(
      fs.readFileSync(tmpConfigPath, { encoding: "utf-8", flag: "r" }),
    ) as {
      builds: Array<{
        build_machine: number;
        run_machine: number;
        recipe_id: number;
        executables?: string[];
      }>;
    };

    expect(result.builds).toHaveLength(2);
    expect(result.builds[0].build_machine).toBe(1);
    expect(result.builds[0].run_machine).toBe(1);
    expect(result.builds[0].recipe_id).toBe(1);
    expect(result.builds[1].build_machine).toBe(2);
    expect(result.builds[1].executables).toEqual(["bin/app"]);
    expect(output).toContain("Builds added");
  });

  test("configure-builds rejects invalid platform IDs", async () => {
    chdir(tmpDirPath);

    const toolModule = await import(buildConfiguringToolModulePath);
    const tool = toolModule.default;

    const output = await tool.execute({
      configFilePath: tmpConfigPath,
      builds: [{ build_machine: 99, run_machine: 1, recipe_id: 1 }],
    });

    expect(output).toContain("build_machine=99");
    expect(output).toContain("Valid platform IDs");
    expect(output).toContain("No changes written");

    // Verify file was NOT modified
    const result = yaml.parse(
      fs.readFileSync(tmpConfigPath, { encoding: "utf-8", flag: "r" }),
    ) as { builds: Array<unknown> };
    expect(result.builds).toHaveLength(2); // still 2 from previous test
  });
});
