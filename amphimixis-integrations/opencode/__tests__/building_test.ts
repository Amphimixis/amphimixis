import { describe, test, expect } from "bun:test";
import tool from "../tools/amphimixis-build";

/**
 * Test that the building tool accepts build_name parameter
 */
describe("Building tool", () => {
  test("tool schema includes build_name", () => {
    expect(tool.args).toHaveProperty("build_name");
    expect(tool.args.project_path).toBeDefined();
    expect(tool.args.config).toBeDefined();
  });

  test("tool description is correct", () => {
    expect(tool.description).toContain("Build project");
  });
});
