"""Tests of LaboratoryAssistant"""

from os import environ, path
from shutil import rmtree

import pytest
import yaml

from amphimixis.core import LaboratoryAssistant
from amphimixis.core.general import (
    Arch,
    CompilerFlagsAttrs,
    MachineAuthenticationInfo,
    MachineInfo,
    Toolchain,
    ToolchainAttrs,
)
from amphimixis.core.laboratory_assistant import (
    _ATTRIBUTES,
    _PLATFORM,
    _PLATFORMS,
    _SYSROOT,
    _SYSROOTS,
    _TARGET_ARCH,
    _TOOLCHAINS,
)


def is_file_exists_and_correct(pth: str) -> bool:
    """Check if file creating correct"""
    is_exists = path.exists(pth)

    is_correct_filled = False
    with open(LaboratoryAssistant.TOOLBOX_PATH, "r", encoding="utf-8") as f_toolbox:
        toolbox = yaml.safe_load(f_toolbox)
        is_correct_filled = {_PLATFORMS, _TOOLCHAINS, _SYSROOTS} == set(
            dict(toolbox).keys()
        )
    return is_exists and is_correct_filled


@pytest.mark.unit
class TestLaboratoryAssistant:

    @pytest.fixture
    def _set_testing_environment(self):
        # set testing environment
        LaboratoryAssistant.CONFIG_DIR_PATH = "/tmp/amphimixis"
        LaboratoryAssistant.TOOLBOX_PATH = "/tmp/amphimixis/toolbox.yml"
        rmtree(LaboratoryAssistant.CONFIG_DIR_PATH, ignore_errors=True)

        yield None

        # cleanup
        rmtree(LaboratoryAssistant.CONFIG_DIR_PATH, ignore_errors=True)
        # set default values to global config paths
        LaboratoryAssistant.CONFIG_DIR_PATH = (
            f"{environ["HOME"]}/.config/amphimixis"
            if environ.get("XDG_CONFIG_HOME") is None
            else f"{environ.get("XDG_CONFIG_HOME")}/amphimixis"
        )
        LaboratoryAssistant.TOOLBOX_PATH = (
            LaboratoryAssistant.CONFIG_DIR_PATH + "/toolbox.yml"
        )

    @pytest.mark.parametrize(
        "platform_name,arch,address,username,password,port",
        [
            ("platka-bianbu", Arch.X86, "333.666.069.404", "bzych", None, 8000),
            (
                "platku-smazhem-bianbu",
                Arch.X86,
                "333.666.069.404",
                "bzych",
                "best-passwd",
                8000,
            ),
        ],
    )
    def test_adding_non_existing_platform_in_toolbox_file(
        self,
        platform_name,
        arch,
        address,
        username,
        password,
        port,
        _set_testing_environment,
    ) -> None:
        """
        Test: Adding two non-existing platform to the toolbox
        Expected: Platforms appeared in the toolbox
        """

        # construct new platform
        machine = MachineInfo(
            arch, address, MachineAuthenticationInfo(username, password, port), None
        )

        # add platform to toolbox via LaboratoryAssistant
        LaboratoryAssistant.add_platform(platform_name, machine)

        # reload from file
        experimental = LaboratoryAssistant.parse_config_file()

        # check that platform was load correct from experimental
        assert experimental[_PLATFORMS][platform_name] == machine.__dictstr__

    @pytest.mark.parametrize(
        "toolchain_name,sysroot,path_cxx_compiler,target_arch",
        [("g++-14-platka", "/", "/bin/g++-14", Arch.RISCV)],
    )
    @pytest.mark.parametrize(
        "build_machine",
        [
            MachineInfo(
                Arch.X86,
                "172.219.91.1",
                MachineAuthenticationInfo(
                    "bzych",
                    None,
                    22,
                ),
                None,
            )
        ],
    )
    def test_adding_not_existing_toolchain_in_toolbox_file_with_specifying_machine_info(
        self,
        toolchain_name,
        sysroot,
        path_cxx_compiler,
        target_arch,
        build_machine,
        _set_testing_environment,
    ) -> None:
        """
        Test: Adding non-existing toolchain to the toolbox with specifying machine info
        Expected: Toolchain appeared in the toolbox
        """

        # 1) construct new toolchain
        target_arch = Arch.RISCV

        toolchain = Toolchain(toolchain_name, sysroot)
        toolchain.set(ToolchainAttrs.CXX_COMPILER, path_cxx_compiler)
        toolchain.set(CompilerFlagsAttrs.CXX_FLAGS, "-ftree-vectorize")

        # 2) add toolchain to toolbox via LaboratoryAssistant
        LaboratoryAssistant.add_toolchain(toolchain, build_machine, target_arch)

        # 3) construct this toolchain as dictionary
        toolchain_data = {
            _ATTRIBUTES: {
                ToolchainAttrs.CXX_COMPILER: path_cxx_compiler,
                CompilerFlagsAttrs.CXX_FLAGS: "-ftree-vectorize",
            },
            _TARGET_ARCH: target_arch.value,
            _SYSROOT: sysroot,
        }

        platform_name = LaboratoryAssistant.find_platform_by_address(
            str(build_machine.address)
        )

        if platform_name:
            toolchain_data[_PLATFORM] = platform_name

        # 3) reload from file
        experimental = LaboratoryAssistant.parse_config_file()

        # 4) check that toolchain was load correct from experimental
        assert experimental[_TOOLCHAINS][toolchain_name] == toolchain_data

    def test_find_existing_platform_by_address(self, _set_testing_environment) -> None:
        """Find platform by address of machine
        Expect: find existing platform"""

        # construct new platform
        platform_name = "platku-smazhem-bianbu"
        platform_address = "8.8.8.8"
        machine = MachineInfo(
            Arch.X86,
            platform_address,
            MachineAuthenticationInfo("bzych", "best-passwd", 8000),
            None,
        )

        # add platform to toolbox via LaboratoryAssistant
        LaboratoryAssistant.add_platform(platform_name, machine)

        # check that platform was load correct from experimental
        assert (
            LaboratoryAssistant.find_platform_by_address(platform_address)
            == platform_name
        )

    def test_find_non_existing_platform_by_address(
        self, _set_testing_environment
    ) -> None:
        """Find non-existing platform by address of machine
        Expect: not found"""

        # construct new platform
        platform_name = "platku-smazhem-bianbu"
        platform_address = "333.666.069.404"
        machine = MachineInfo(
            Arch.X86,
            platform_address,
            MachineAuthenticationInfo("bzych", "best-passwd", 8000),
            None,
        )

        # add platform to toolbox via LaboratoryAssistant
        LaboratoryAssistant.add_platform(platform_name, machine)

        # set address of non-existing platform
        platform_address = "192.068.323.17"

        # check that platform not in toolbox
        assert not LaboratoryAssistant.find_platform_by_address(platform_address)

    def test_creating_dir(self, _set_testing_environment) -> None:
        """
        Remove f"{LaboratoryAssistant.CONFIG_DIR_PATH}" and call _parse_config_file()
        Expected: create directory f"{LaboratoryAssistant.CONFIG_DIR_PATH}"
        """
        LaboratoryAssistant.parse_config_file()
        assert path.exists(LaboratoryAssistant.CONFIG_DIR_PATH)

    def test_creating_file(self, _set_testing_environment) -> None:
        """
        Remove f"LaboratoryAssistant.CONFIG_DIR_PATH}/toolbox.yml" and call _parse_config_file()
        Expected: create file f"{LaboratoryAssistant.CONFIG_DIR_PATH}/toolbox.yml" and fill it correct
        """
        LaboratoryAssistant.parse_config_file()
        assert is_file_exists_and_correct(LaboratoryAssistant.TOOLBOX_PATH)

    def test_creating_dir_and_file(self, _set_testing_environment):
        """Test if directory and file creating correct"""
        LaboratoryAssistant.parse_config_file()

        assert path.exists(LaboratoryAssistant.CONFIG_DIR_PATH)
        assert is_file_exists_and_correct(LaboratoryAssistant.TOOLBOX_PATH)
