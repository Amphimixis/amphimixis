import { describe, test, expect } from "bun:test";
import tool from "../tools/amphimixis-profile";

/**
 * Test that the profiling tool accepts build_name parameter
 */
describe("Profiling tool", () => {
  test("tool schema includes build_name", () => {
    expect(tool.args).toHaveProperty("build_name");
    expect(tool.args.project_path).toBeDefined();
    expect(tool.args.config).toBeDefined();
  });

  test("tool description is correct", () => {
    expect(tool.description).toContain("Profile project");
  });
});
