"""Tests for build systems: CMake, Make, Ninja"""

import os
import pytest

from unittest.mock import MagicMock, patch


from amphimixis.core.build_systems.cmake import CMake
from amphimixis.core.build_systems.make import Make
from amphimixis.core.build_systems.ninja import Ninja
from amphimixis.core.general import (
    Arch,
    Build,
    CompilerFlags,
    CompilerFlagsAttrs,
    MachineInfo,
    Project,
    Toolchain,
    ToolchainAttrs,
)


@pytest.fixture
def local_machine():
    return MachineInfo(Arch.X86, None, None, None)


@pytest.fixture
def remote_machine():
    return MachineInfo(Arch.X86, "192.168.1.100", None, None)


@pytest.fixture
def mock_project(tmp_path):
    return Project(path=str(tmp_path))


root = "/mock"
source = os.path.join(root, "source")
file = os.path.join(source, "file")


@pytest.fixture
def mock_shell():
    shell_mock = MagicMock()
    shell_mock.get_project_workdir.return_value = "/mock/builds/project_build"
    shell_mock.get_source_dir.return_value = "/mock/source"
    shell_mock.connect.return_value = shell_mock
    shell_mock.run.return_value = (0, [["4"]], [[""]])
    return shell_mock


@pytest.mark.unit
class TestMake:
    """Tests for Make build system"""

    @pytest.fixture
    def make_system(self, mock_project, mock_shell):
        with patch("amphimixis.core.build_systems.make.Shell", return_value=mock_shell):
            make = Make(mock_project)
            yield make

    @pytest.mark.parametrize(
        "flag_attr,flag_value,expected_flag",
        [
            (CompilerFlagsAttrs.C_FLAGS, "-O2", "CFLAGS='-O2'"),
            (CompilerFlagsAttrs.CXX_FLAGS, "-Wall", "CXXFLAGS='-Wall'"),
            (
                CompilerFlagsAttrs.FORTRAN_FLAGS,
                "-ffast-math",
                "FCFLAGS='-ffast-math'",
            ),
        ],
    )
    def test_generate_lang_flags(
        self, make_system, flag_attr, flag_value, expected_flag
    ):
        compiler_flags = CompilerFlags()
        compiler_flags.set(flag_attr, flag_value)
        result = make_system._generate_lang_flags(compiler_flags)
        assert expected_flag in result

    @pytest.mark.parametrize(
        "tool_attr,expected_tool",
        [
            (ToolchainAttrs.C_COMPILER, "CC"),
            (ToolchainAttrs.CXX_COMPILER, "CXX"),
            (ToolchainAttrs.FORTRAN_COMPILER, "FC"),
            (ToolchainAttrs.AR_T, "AR"),
            (ToolchainAttrs.LD_T, "LD"),
        ],
    )
    def test_toolchain_attrs_map(self, make_system, tool_attr, expected_tool):
        result = make_system._attrs_map(tool_attr.value)
        assert result == expected_tool

    @pytest.mark.parametrize(
        "compiler,flags,expected",
        [
            (ToolchainAttrs.C_COMPILER, "/usr/bin/gcc", "CC='/usr/bin/gcc'"),
            (ToolchainAttrs.CXX_COMPILER, "/usr/bin/g++", "CXX='/usr/bin/g++'"),
        ],
    )
    def test_generate_toolchain_flags(self, make_system, compiler, flags, expected):
        toolchain = Toolchain()
        toolchain.set(compiler, flags)
        result = make_system._generate_toolchain_flags(toolchain)
        assert expected in result

    def test_sysroot_handling(self, mock_project, mock_shell):
        sysroot = "/sysroot"
        toolchain = Toolchain(sysroot=sysroot)
        toolchain.set(ToolchainAttrs.C_COMPILER, "/usr/bin/gcc")

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None, None),
            run_machine=MachineInfo(Arch.X86, None, None, None),
            build_name="test_build",
            executables=[],
            toolchain=toolchain,
            sysroot=sysroot,
            compiler_flags=None,
            config_flags=None,
        )

        with (
            patch("amphimixis.core.build_systems.make.Shell", return_value=mock_shell),
            patch(
                "amphimixis.core.build_systems.make.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            make = Make(mock_project)
            make._build_install_clean(build, configure=True)

        calls = [str(call) for call in mock_shell.run.call_args_list]
        combined_output = " ".join(calls)
        assert "SYSROOT='/sysroot'" in combined_output

    def test_parallel_build(self, mock_project, mock_shell):
        jobs = 1
        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None, None),
            run_machine=MachineInfo(Arch.X86, None, None, None),
            build_name="test_build",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags=None,
            jobs=jobs,
        )

        with patch("amphimixis.core.build_systems.make.Shell", return_value=mock_shell):
            make = Make(mock_project)
            make._build_install_clean(build, configure=False)

        calls = [str(call) for call in mock_shell.run.call_args_list]
        combined_output = " ".join(calls)
        assert f"--jobs={jobs}" in combined_output

    def test_warning_on_build(self, mock_project, mock_shell):
        with (
            patch("amphimixis.core.build_systems.make.Shell", return_value=mock_shell),
            patch(
                "amphimixis.core.build_systems.make.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            make = Make(mock_project)
            make._ui = MagicMock()
            make.build(
                Build(
                    build_machine=MachineInfo(Arch.X86, None, None, None),
                    run_machine=MachineInfo(Arch.X86, None, None, None),
                    build_name="test",
                    executables=[],
                    toolchain=None,
                    sysroot=None,
                    compiler_flags=None,
                    config_flags=None,
                )
            )
            assert make._ui.send_warning.call_count == 1


@pytest.mark.unit
class TestNinja:
    """Tests for Ninja build system"""

    def test_parallel_build(self, mock_project, mock_shell):
        jobs = 1
        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None, None),
            run_machine=MachineInfo(Arch.X86, None, None, None),
            build_name="test_build",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags=None,
            jobs=jobs,
        )

        with patch(
            "amphimixis.core.build_systems.ninja.Shell", return_value=mock_shell
        ):
            ninja = Ninja(mock_project)
            ninja.run_building(build)

        calls = [str(call) for call in mock_shell.run.call_args_list]
        combined_output = " ".join(calls)
        assert f"-j {jobs}" in combined_output


@pytest.mark.unit
class TestCMake:
    """Tests for CMake build system"""

    @pytest.fixture
    def cmake_system(self, mock_project, mock_shell):
        with patch(
            "amphimixis.core.build_systems.cmake.Shell", return_value=mock_shell
        ):
            ninja_runner = Ninja(mock_project)
            cmake = CMake(mock_project, runner=ninja_runner)
            yield cmake

    @pytest.mark.parametrize(
        "flag_attr,flag_value,expected_flag",
        [
            (CompilerFlagsAttrs.C_FLAGS, "-O2", "-DCMAKE_C_FLAGS='-O2'"),
            (CompilerFlagsAttrs.CXX_FLAGS, "-Wall", "-DCMAKE_CXX_FLAGS='-Wall'"),
            (
                CompilerFlagsAttrs.CUDA_FLAGS,
                "-arch=sm_80",
                "-DCMAKE_CUDA_FLAGS='-arch=sm_80'",
            ),
        ],
    )
    def test_generate_flags(self, cmake_system, flag_attr, flag_value, expected_flag):
        compiler_flags = CompilerFlags()
        compiler_flags.set(flag_attr, flag_value)
        result = cmake_system._generate_lang_flags(compiler_flags)
        assert expected_flag in result

    @pytest.mark.parametrize(
        "tool_attr,tool_value,expected_flag",
        [
            (
                ToolchainAttrs.C_COMPILER,
                "/usr/bin/gcc",
                "-DCMAKE_C_COMPILER='/usr/bin/gcc'",
            ),
            (
                ToolchainAttrs.CXX_COMPILER,
                "/usr/bin/g++",
                "-DCMAKE_CXX_COMPILER='/usr/bin/g++'",
            ),
            (ToolchainAttrs.AR_T, "/usr/bin/ar", "-DCMAKE_AR='/usr/bin/ar'"),
        ],
    )
    def test_generate_toolchain_flags(
        self, cmake_system, tool_attr, tool_value, expected_flag
    ):
        toolchain = Toolchain()
        toolchain.set(tool_attr, tool_value)
        result = cmake_system._generate_toolchain_flags(toolchain)
        assert expected_flag in result

    def test_parallel_build(self, mock_project, mock_shell):
        jobs = 1
        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None, None),
            run_machine=MachineInfo(Arch.X86, None, None, None),
            build_name="test_build",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags=None,
            jobs=jobs,
        )

        with (
            patch("amphimixis.core.build_systems.cmake.Shell", return_value=mock_shell),
            patch(
                "amphimixis.core.build_systems.cmake.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            cmake = CMake(mock_project, Ninja(mock_project))
            cmake.build(build)

        calls = [str(call) for call in mock_shell.run.call_args_list]
        combined_output = " ".join(calls)
        assert f"--parallel {jobs}" in combined_output

    def test_sysroot_in_command(self, mock_project, mock_shell):
        sysroot = "/sysroot"
        toolchain = Toolchain(sysroot=sysroot)
        toolchain.set(ToolchainAttrs.C_COMPILER, "/usr/bin/gcc")

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None, None),
            run_machine=MachineInfo(Arch.X86, None, None, None),
            build_name="cmake_build",
            executables=[],
            toolchain=toolchain,
            sysroot=sysroot,
            compiler_flags=None,
            config_flags=None,
        )

        with (
            patch("amphimixis.core.build_systems.cmake.Shell", return_value=mock_shell),
            patch(
                "amphimixis.core.build_systems.cmake.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            ninja_runner = Ninja(mock_project)
            cmake = CMake(mock_project, runner=ninja_runner)
            cmake.build(build)

        calls = [str(call) for call in mock_shell.run.call_args_list]
        combined_output = " ".join(calls)
        assert "-DCMAKE_SYSROOT='/sysroot'" in combined_output

    def test_generator_selection_ninja(self, mock_project, mock_shell):
        with (
            patch("amphimixis.core.build_systems.cmake.Shell", return_value=mock_shell),
            patch(
                "amphimixis.core.build_systems.cmake.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            ninja_runner = Ninja(mock_project)
            cmake = CMake(mock_project, runner=ninja_runner)

            build = Build(
                build_machine=MachineInfo(Arch.X86, None, None, None),
                run_machine=MachineInfo(Arch.X86, None, None, None),
                build_name="test",
                executables=[],
                toolchain=None,
                sysroot=None,
                compiler_flags=None,
                config_flags=None,
            )
            cmake.build(build)

            calls = [str(call) for call in mock_shell.run.call_args_list]
            combined_output = " ".join(calls)
            assert "-G Ninja" in combined_output

    def test_generator_selection_make(self, mock_project, mock_shell):
        with (
            patch("amphimixis.core.build_systems.cmake.Shell", return_value=mock_shell),
            patch(
                "amphimixis.core.build_systems.cmake.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            make_runner = Make(mock_project)
            cmake = CMake(mock_project, runner=make_runner)

            build = Build(
                build_machine=MachineInfo(Arch.X86, None, None, None),
                run_machine=MachineInfo(Arch.X86, None, None, None),
                build_name="test",
                executables=[],
                toolchain=None,
                sysroot=None,
                compiler_flags=None,
                config_flags=None,
            )
            cmake.build(build)

            calls = [str(call) for call in mock_shell.run.call_args_list]
            combined_output = " ".join(calls)
            assert '-G "Unix Makefiles"' in combined_output

    def test_config_flags_passed(self, mock_project, mock_shell):
        with (
            patch("amphimixis.core.build_systems.cmake.Shell", return_value=mock_shell),
            patch(
                "amphimixis.core.build_systems.cmake.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            ninja_runner = Ninja(mock_project)
            cmake = CMake(mock_project, runner=ninja_runner)

            build = Build(
                build_machine=MachineInfo(Arch.X86, None, None, None),
                run_machine=MachineInfo(Arch.X86, None, None, None),
                build_name="test",
                executables=[],
                toolchain=None,
                sysroot=None,
                compiler_flags=None,
                config_flags="-DCMAKE_BUILD_TYPE=Release",
            )
            cmake.build(build)

        calls = [str(call) for call in mock_shell.run.call_args_list]
        combined_output = " ".join(calls)
        assert "CMAKE_BUILD_TYPE=Release" in combined_output

    def test_cmake_and_build_steps(self, cmake_system, mock_shell):
        mock_shell.run.side_effect = [
            (0, [["Configuring..."]], [[""]]),
            (0, [["Building..."]], [[""]]),
        ]

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None, None),
            run_machine=MachineInfo(Arch.X86, None, None, None),
            build_name="test",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags=None,
        )

        with patch(
            "amphimixis.core.build_systems.cmake.BuildSystem.find_relative_path",
            return_value=file,
        ):
            cmake_system.build(build)

        assert mock_shell.run.call_count >= 2


@pytest.mark.unit
class TestBuildSystemIntegration:
    """Integration tests for build system command generation"""

    def test_toolchain_and_flags_combined(self, mock_project, mock_shell):
        toolchain = Toolchain()
        toolchain.set(ToolchainAttrs.C_COMPILER, "/custom/gcc")
        toolchain.set(ToolchainAttrs.CXX_COMPILER, "/custom/g++")

        compiler_flags = CompilerFlags()
        compiler_flags.set(CompilerFlagsAttrs.C_FLAGS, "-O3")

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None, None),
            run_machine=MachineInfo(Arch.X86, None, None, None),
            build_name="test",
            executables=[],
            toolchain=toolchain,
            sysroot=None,
            compiler_flags=compiler_flags,
            config_flags=None,
        )

        with (
            patch("amphimixis.core.build_systems.make.Shell", return_value=mock_shell),
            patch(
                "amphimixis.core.build_systems.make.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            make = Make(mock_project)
            make._build_install_clean(build, configure=True)

        calls = [str(call) for call in mock_shell.run.call_args_list]
        combined_output = " ".join(calls)
        assert "/custom/gcc" in combined_output
        assert "/custom/g++" in combined_output
        assert "-O3" in combined_output
