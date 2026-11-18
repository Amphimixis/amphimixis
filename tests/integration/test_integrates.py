"""Integration tests for amphimixis"""

import os
from pathlib import Path

import pytest

import amphimixis
from amphimixis import general
from amphimixis.amixis.commands.build import run_build

NAME_EXECUTABLE_FILE = "a.out"
NAME_FILE_C_PROGRAM = "main.c"
SIMPLE_C_PROGRAM_SUCCESS = "int main() {return 0;}"
SIMPLE_C_PROGRAM_FAIL = "int main() {return 0}"
NAME_BUILD_CONFIG_FILE = "CMakeLists.txt"
SIMPLE_CMAKELIST = (
    "cmake_minimum_required(VERSION 3.5)\nproject(a.out)\nadd_executable(a.out main.c)"
)
CONFIG_FILE = (
    "build_system:  CMake\nrunner: Make\nplatforms:\n- id: 1\n  arch: x86\n  username: testuser\n  port: 22\n  password: testpass"
    '\n\nrecipes:\n- id: 1\n  config_flags:\n  compiler_flags:\n  cxx_flags: "-O2"\n\nbuilds:\n- build_machine: 1\n'
    '  toolchain:\n    cxx_compiler: "/usr/bin/g++"\n  sysroot: "/"\n  run_machine: 1\n  recipe_id: 1'
)


@pytest.mark.integration
@pytest.mark.parametrize(
    "program_source, expected_result",
    [
        (SIMPLE_C_PROGRAM_SUCCESS, True),
        (SIMPLE_C_PROGRAM_FAIL, False),
    ],
)
def test_between_configurator_and_builder(
    create_working_space, create_file, program_source, expected_result
):
    project_dir = create_working_space()
    create_file(NAME_FILE_C_PROGRAM, program_source, project_dir)
    create_file(NAME_BUILD_CONFIG_FILE, SIMPLE_CMAKELIST, project_dir)

    working_dir = create_working_space()
    create_file("input.yaml", CONFIG_FILE, working_dir)
    config_file = working_dir / "input.yaml"

    build = general.Build(
        general.MachineInfo(general.Arch.X86, None, None, None),
        general.MachineInfo(general.Arch.X86, None, None, None),
        "test_build",
        [NAME_EXECUTABLE_FILE],
        None,
        None,
        None,
        None,
    )

    project = general.Project(str(project_dir), [build])
    runner = amphimixis.build_systems_dict["cmake"][1][0](project)
    project.build_system = amphimixis.build_systems_dict["cmake"][0](project, runner)

    orig_dir = Path.cwd()
    try:
        os.chdir(working_dir)
        result = run_build(project, config_file)
        assert result == expected_result
    finally:
        os.chdir(orig_dir)
