"""Tests for build systems: Autoconf, CMake, Make, Ninja"""

import os
import pytest

from unittest.mock import MagicMock, patch


from amphimixis.core.build_systems.autoconf import Autoconf
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
    return MachineInfo(Arch.X86, None, None)


@pytest.fixture
def remote_machine():
    return MachineInfo(Arch.X86, "192.168.1.100", None)


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
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
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
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
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
                    build_machine=MachineInfo(Arch.X86, None, None),
                    run_machine=MachineInfo(Arch.X86, None, None),
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
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
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
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
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
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
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
                build_machine=MachineInfo(Arch.X86, None, None),
                run_machine=MachineInfo(Arch.X86, None, None),
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
                build_machine=MachineInfo(Arch.X86, None, None),
                run_machine=MachineInfo(Arch.X86, None, None),
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
                build_machine=MachineInfo(Arch.X86, None, None),
                run_machine=MachineInfo(Arch.X86, None, None),
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
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
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
class TestAutoconf:
    """Tests for Autoconf build system"""

    @pytest.fixture
    def autoconf_system(self, mock_project):
        return Autoconf(mock_project)

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
        self, autoconf_system, flag_attr, flag_value, expected_flag
    ):
        compiler_flags = CompilerFlags()
        compiler_flags.set(flag_attr, flag_value)
        result = autoconf_system._generate_lang_flags(compiler_flags)
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
    def test_toolchain_attrs_map(self, autoconf_system, tool_attr, expected_tool):
        result = autoconf_system._attrs_map(tool_attr.value)
        assert result == expected_tool

    @pytest.mark.parametrize(
        "compiler,flags,expected",
        [
            (ToolchainAttrs.C_COMPILER, "/usr/bin/gcc", "CC='/usr/bin/gcc'"),
            (ToolchainAttrs.CXX_COMPILER, "/usr/bin/g++", "CXX='/usr/bin/g++'"),
        ],
    )
    def test_generate_toolchain_flags(self, autoconf_system, compiler, flags, expected):
        toolchain = Toolchain()
        toolchain.set(compiler, flags)
        result = autoconf_system._generate_toolchain_flags(toolchain)
        assert expected in result

    def test_sysroot_in_command(self, mock_project, mock_shell):
        sysroot = "/sysroot"
        toolchain = Toolchain(sysroot=sysroot)
        toolchain.set(ToolchainAttrs.C_COMPILER, "/usr/bin/gcc")

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
            build_name="autoconf_build",
            executables=[],
            toolchain=toolchain,
            sysroot=sysroot,
            compiler_flags=None,
            config_flags=None,
        )

        runner = MagicMock()
        runner.run_building.return_value = (0, "", "")

        with (
            patch(
                "amphimixis.core.build_systems.autoconf.Shell",
                return_value=mock_shell,
            ),
            patch(
                "amphimixis.core.build_systems.autoconf.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            autoconf = Autoconf(mock_project, runner=runner)
            autoconf.build(build)

        calls = [str(call) for call in mock_shell.run.call_args_list]
        combined_output = " ".join(calls)
        assert "SYSROOT='/sysroot'" in combined_output

    def test_config_flags_passed(self, mock_project, mock_shell):
        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
            build_name="test",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags="--enable-static",
        )

        runner = MagicMock()
        runner.run_building.return_value = (0, "", "")

        with (
            patch(
                "amphimixis.core.build_systems.autoconf.Shell",
                return_value=mock_shell,
            ),
            patch(
                "amphimixis.core.build_systems.autoconf.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            autoconf = Autoconf(mock_project, runner=runner)
            autoconf.build(build)

        calls = [str(call) for call in mock_shell.run.call_args_list]
        combined_output = " ".join(calls)
        assert "--enable-static" in combined_output

    def test_configure_and_build_steps(self, mock_project, mock_shell):
        runner = MagicMock()
        runner.run_building.return_value = (0, "", "")

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
            build_name="test",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags=None,
        )

        with (
            patch(
                "amphimixis.core.build_systems.autoconf.Shell",
                return_value=mock_shell,
            ),
            patch(
                "amphimixis.core.build_systems.autoconf.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            autoconf = Autoconf(mock_project, runner=runner)
            autoconf.build(build)

        assert mock_shell.run.call_count >= 2

    def test_runner_called(self, mock_project, mock_shell):
        runner = MagicMock()
        runner.run_building.return_value = (0, "built", "")

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
            build_name="test",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags=None,
        )

        with (
            patch(
                "amphimixis.core.build_systems.autoconf.Shell",
                return_value=mock_shell,
            ),
            patch(
                "amphimixis.core.build_systems.autoconf.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            autoconf = Autoconf(mock_project, runner=runner)
            err, stdout, _ = autoconf.build(build)

        assert runner.run_building.call_count == 1
        assert err == 0
        assert "built" in stdout

    def test_autoreconf_run_when_configure_missing(self, mock_project, mock_shell):
        source_dir = mock_shell.get_source_dir()
        before = set()
        after = {
            os.path.join(source_dir, "configure"),
            os.path.join(source_dir, "Makefile.in"),
            os.path.join(source_dir, "aclocal.m4"),
        }

        runner = MagicMock()
        runner.run_building.return_value = (0, "built", "")

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
            build_name="test",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags=None,
        )

        with patch(
            "amphimixis.core.build_systems.autoconf.Shell",
            return_value=mock_shell,
        ):
            autoconf = Autoconf(mock_project, runner=runner)
            autoconf._list_source_paths = MagicMock(side_effect=[before, after])
            autoconf._find_autoconf_dir = MagicMock(return_value=source_dir)
            autoconf._generate_configure = MagicMock(
                return_value=(0, [["generated"]], [[""]])
            )
            autoconf._clean_source_paths = MagicMock()

            err, stdout, _ = autoconf.build(build)

        assert err == 0
        assert "built" in stdout
        autoconf._generate_configure.assert_called_once()
        autoconf._clean_source_paths.assert_called_once_with(mock_shell, after - before)

    def test_autogen_sh_used_when_present(self, mock_project, mock_shell):
        autoconf = Autoconf(mock_project)
        mock_shell.run.side_effect = [
            (0, [[""]], [[""]]),
            (0, [["autogen output"]], [[""]]),
        ]

        autoconf._generate_configure(mock_shell, "/mock/source")

        combined = " ".join(str(call) for call in mock_shell.run.call_args_list)
        assert "./autogen.sh" in combined
        assert "autoreconf" not in combined

    def test_bootstrap_used_when_autogen_missing(self, mock_project, mock_shell):
        autoconf = Autoconf(mock_project)
        mock_shell.run.side_effect = [
            (1, [[""]], [[""]]),
            (0, [[""]], [[""]]),
            (0, [["bootstrap output"]], [[""]]),
        ]

        autoconf._generate_configure(mock_shell, "/mock/source")

        calls = mock_shell.run.call_args_list
        assert len(calls) == 3
        combined = " ".join(str(call) for call in calls)
        assert "./bootstrap" in combined
        assert "autoreconf" not in combined
        assert "./autogen.sh" not in combined

    def test_autoreconf_fallback_when_no_generation_script(
        self, mock_project, mock_shell
    ):
        autoconf = Autoconf(mock_project)
        mock_shell.run.side_effect = [
            (1, [[""]], [[""]]),
            (1, [[""]], [[""]]),
            (0, [["autoreconf output"]], [[""]]),
        ]

        autoconf._generate_configure(mock_shell, "/mock/source")

        calls = mock_shell.run.call_args_list
        assert len(calls) == 3
        combined = " ".join(str(call) for call in calls)
        assert "autoreconf --install" in combined
        assert "./bootstrap" not in combined

    def test_find_autoconf_dir_prefers_top_level(self, mock_project, mock_shell):
        autoconf = Autoconf(mock_project)
        mock_shell.run.side_effect = [
            (
                0,
                [
                    [
                        "/mock/source/gold/configure.ac",
                        "/mock/source/configure.ac",
                        "/mock/source/gdb/configure.ac",
                    ]
                ],
                [[""]],
            )
        ]

        assert autoconf._find_autoconf_dir(mock_shell, "/mock/source") == "/mock/source"

    def test_find_autoconf_dir_nested_only(self, mock_project, mock_shell):
        autoconf = Autoconf(mock_project)
        mock_shell.run.side_effect = [
            (
                0,
                [
                    [
                        "/mock/source/gold/configure.ac",
                        "/mock/source/gdb/configure.ac",
                    ]
                ],
                [[""]],
            )
        ]

        result = autoconf._find_autoconf_dir(mock_shell, "/mock/source")
        assert result == "/mock/source/gdb"

    def test_no_generation_when_configure_exists(self, mock_project, mock_shell):
        source_dir = mock_shell.get_source_dir()
        before = {
            os.path.join(source_dir, "configure"),
            os.path.join(source_dir, "Makefile.in"),
        }

        runner = MagicMock()
        runner.run_building.return_value = (0, "built", "")

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
            build_name="test",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags=None,
        )

        with (
            patch(
                "amphimixis.core.build_systems.autoconf.Shell",
                return_value=mock_shell,
            ),
            patch(
                "amphimixis.core.build_systems.autoconf.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            autoconf = Autoconf(mock_project, runner=runner)
            autoconf._list_source_paths = MagicMock(return_value=before)
            autoconf._find_autoconf_dir = MagicMock(return_value=source_dir)
            autoconf._generate_configure = MagicMock(return_value=(0, [[""]], [[""]]))
            autoconf._clean_source_paths = MagicMock()

            err, stdout, _ = autoconf.build(build)

        assert err == 0
        assert "built" in stdout
        autoconf._generate_configure.assert_not_called()
        autoconf._clean_source_paths.assert_not_called()

    def test_generation_failure_returns_error_and_cleans(
        self, mock_project, mock_shell
    ):
        source_dir = mock_shell.get_source_dir()
        before = set()
        after = {os.path.join(source_dir, "configure")}

        runner = MagicMock()
        runner.run_building.return_value = (0, "built", "")

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
            build_name="test",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags=None,
        )

        with patch(
            "amphimixis.core.build_systems.autoconf.Shell",
            return_value=mock_shell,
        ):
            autoconf = Autoconf(mock_project, runner=runner)
            autoconf._list_source_paths = MagicMock(side_effect=[before, after])
            autoconf._find_autoconf_dir = MagicMock(return_value=source_dir)
            autoconf._generate_configure = MagicMock(
                return_value=(1, [["gen stdout"]], [["gen stderr"]])
            )
            autoconf._clean_source_paths = MagicMock()

            err, stdout, stderr = autoconf.build(build)

        assert err == 1
        assert "gen stdout" in stdout
        assert "gen stderr" in stderr
        autoconf._clean_source_paths.assert_called_once_with(mock_shell, after)
        runner.run_building.assert_not_called()

    def test_generated_autotools_files_cleaned(self, mock_project, mock_shell):
        source_dir = mock_shell.get_source_dir()
        runner = MagicMock()
        runner.run_building.return_value = (0, "built", "")

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
            build_name="test",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags=None,
        )

        mock_shell.run.side_effect = [
            (0, [["/mock/source/tests/"]], [[""]]),
            (0, [["/mock/source/configure.ac"]], [[""]]),
            (1, [[""]], [[""]]),
            (1, [[""]], [[""]]),
            (0, [["generated"]], [[""]]),
            (
                0,
                [
                    [
                        "/mock/source/tests/",
                        "/mock/source/configure",
                        "/mock/source/Makefile.in",
                        "/mock/source/aclocal.m4",
                    ]
                ],
                [[""]],
            ),
            (0, [], []),
            (0, [["cfg"]], [[""]]),
            (0, [], []),
        ]

        with (
            patch(
                "amphimixis.core.build_systems.autoconf.Shell",
                return_value=mock_shell,
            ),
            patch(
                "amphimixis.core.build_systems.autoconf.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            autoconf = Autoconf(mock_project, runner=runner)
            err, stdout, _ = autoconf.build(build)

        assert err == 0
        assert "built" in stdout
        assert runner.run_building.call_count == 1

        calls = [str(call) for call in mock_shell.run.call_args_list]
        assert "find /mock/source/ -mindepth 1" in calls[0]
        assert "find /mock/source/ -mindepth 1" in calls[5]
        assert "test -f /mock/source/autogen.sh" in calls[2]
        assert "test -f /mock/source/bootstrap" in calls[3]
        assert "autoreconf --install" in calls[4]
        assert "cd /mock/builds/project_build/test" in calls[6]
        assert "rm -rf /mock/source/" in calls[8]
        assert "/mock/source/Makefile.in" in calls[8]
        assert "/mock/source/aclocal.m4" in calls[8]
        assert "/mock/source/configure" in calls[8]
        assert "tests/" not in calls[8]

    def test_warning_on_build(self, mock_project, mock_shell):
        runner = MagicMock()
        runner.run_building.return_value = (0, "", "")

        build = Build(
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
            build_name="test",
            executables=[],
            toolchain=None,
            sysroot=None,
            compiler_flags=None,
            config_flags=None,
        )

        with (
            patch(
                "amphimixis.core.build_systems.autoconf.Shell",
                return_value=mock_shell,
            ),
            patch(
                "amphimixis.core.build_systems.autoconf.BuildSystem.find_relative_path",
                return_value=file,
            ),
        ):
            autoconf = Autoconf(mock_project, runner=runner)
            autoconf._ui = MagicMock()
            autoconf.build(build)

        assert autoconf._ui.send_warning.call_count == 1


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
            build_machine=MachineInfo(Arch.X86, None, None),
            run_machine=MachineInfo(Arch.X86, None, None),
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
