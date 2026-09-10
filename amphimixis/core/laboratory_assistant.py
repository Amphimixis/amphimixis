"""Class that manages and provides toolchains, sysroots and platforms."""

from os import environ, makedirs
from os.path import exists

import yaml

from amphimixis.core import logger
from amphimixis.core.general.general import (
    Arch,
    CompilerFlagsAttrs,
    MachineAuthenticationInfo,
    MachineInfo,
    Toolchain,
    ToolchainAttrs,
)

_logger = logger.setup_logger("LABORATORY_ASSISTANT")

_PLATFORMS = "platforms"
_SYSROOTS = "sysroots"
_TOOLCHAINS = "toolchains"

_PLATFORM = "platform"
_SYSROOT = "sysroot"
_ADDRESS = "address"
_PORT = "port"
_ARCH = "arch"
_AUTH = "auth"
_USERNAME = "username"
_PASSWORD = "password"
_TARGET_ARCH = "target_arch"
_ATTRIBUTES = "attributes"

_STD_INDENT = 4


class LaboratoryAssistant:
    """Manager of toolchains, sysroots and platforms in Amphimixis global config."""

    CONFIG_DIR_PATH = (
        f"{environ["HOME"]}/.config/amphimixis"
        if environ.get("XDG_CONFIG_HOME") is None
        else f"{environ.get("XDG_CONFIG_HOME")}/amphimixis"
    )

    TOOLBOX_PATH = CONFIG_DIR_PATH + "/toolbox.yml"

    @staticmethod
    def parse_config_file() -> dict:
        """Search ~/.config/amphimixis/toolbox.yml and parse or create it.

        :rtype: dict
        :return: Toolbox content from Amphimixis global config
        """
        template: dict[str, dict] = {
            _PLATFORMS: {},
            _TOOLCHAINS: {},
            _SYSROOTS: {},
        }
        makedirs(LaboratoryAssistant.CONFIG_DIR_PATH, exist_ok=True)
        if exists(f"{LaboratoryAssistant.TOOLBOX_PATH}"):
            with open(
                f"{LaboratoryAssistant.TOOLBOX_PATH}",
                encoding="utf-8",
            ) as f_toolbox:
                _toolbox = yaml.safe_load(f_toolbox) or {}
                if set(_toolbox.keys()) == {_PLATFORMS, _TOOLCHAINS, _SYSROOTS}:
                    return _toolbox

                template |= _toolbox

        LaboratoryAssistant._dump_config(template)
        return template

    @staticmethod
    def _dump_config(toolbox: dict) -> None:
        with open(
            f"{LaboratoryAssistant.TOOLBOX_PATH}",
            "w",
            encoding="utf-8",
        ) as config_file:
            yaml.safe_dump(toolbox, config_file, indent=_STD_INDENT)

    @staticmethod
    def find_platform(platform_name: str) -> MachineInfo | None:
        """Find platform in Amphimixis global config (toolbox) by name.

        :param str platform_name: Name of platform
        :rtype: MachineInfo | None
        :return: info about machine if found else None
        """
        _toolbox = LaboratoryAssistant.parse_config_file()
        if platform_name in _toolbox[_PLATFORMS]:
            machine = _toolbox[_PLATFORMS][platform_name]
            auth = None
            if _AUTH in machine:
                auth = MachineAuthenticationInfo(
                    machine[_AUTH][_USERNAME],
                    machine[_AUTH].get(_PASSWORD, None),
                    machine[_AUTH][_PORT],
                )
            return MachineInfo(
                Arch(machine[_ARCH]),
                machine.get(_ADDRESS, None),
                auth,
            )
        return None

    @staticmethod
    def find_platform_by_address(address: str) -> str:
        """Find platform in Amphimixis global config (toolbox) by address.

        :param str address: Address of platform in network
        :rtype: str
        :return: platform name if platform exists else empty string
        """
        _toolbox = LaboratoryAssistant.parse_config_file()
        for name, machine in _toolbox[_PLATFORMS].items():
            if machine.get(_ADDRESS, None) == address:
                return name
        return ""

    @staticmethod
    def add_platform(name: str, machine: MachineInfo) -> bool:
        """Add platform to Amphimixis global config (toolbox).

        :param str name: Name of platform
        :param MachineInfo machine: Information about machine to write to global config
        :rtype: bool
        :return: True if platform successfully added to global config
        """
        _toolbox = LaboratoryAssistant.parse_config_file()
        _toolbox[_PLATFORMS][name] = machine.__dictstr__
        try:
            LaboratoryAssistant._dump_config(_toolbox)
            return True
        except FileExistsError:
            _logger.error("Error with writing to config file")
            return False

    @staticmethod
    def delete_platform(name: str) -> None:
        """Delete platform from Amphimixis global config by name.

        :param str name: Name of platform
        """
        toolbox = LaboratoryAssistant.parse_config_file()
        toolbox[_PLATFORMS].pop(name)

    @staticmethod
    def find_toolchain_by_name(name: str) -> Toolchain | None:
        """Find toolchain by name in global config.

        :param str name: name of toolchain in global config
        :rtype: Toolchain | None
        :return: Toolchain constructed from Amphimixis global config found by name,
            ``None`` if not found
        """
        toolbox: dict = LaboratoryAssistant.parse_config_file()
        if name in toolbox[_TOOLCHAINS]:
            d_toolchain: dict = toolbox[_TOOLCHAINS][name]
            toolchain = Toolchain(name, d_toolchain[_SYSROOT])
            for attr, value in d_toolchain[_ATTRIBUTES].items():
                if attr in ToolchainAttrs:
                    toolchain.set(ToolchainAttrs(attr), value)
                else:
                    toolchain.set(CompilerFlagsAttrs(attr), value)
            return toolchain

        return None  # if not found in global config

    @staticmethod
    def add_toolchain(
        toolchain: Toolchain,
        machine: MachineInfo | str,
        target_arch: Arch,
    ) -> bool:
        """Add toolchain to Amphimixis global config (toolbox).

        :param Toolchain toolchain: Toolchain to adding
        :param MachineInfo | str machine: Platform that contains toolchain
        :param Arch target_arch: The architecture for that the toolchain generates code
        :rtype: bool
        :return: True if toolchain successfully added to global config
        """
        if not toolchain.data:
            return False

        toolchain_data: dict[str, str | dict[str, str]] = {}
        platform_name: str
        if isinstance(machine, str):
            if LaboratoryAssistant.find_platform(machine) is None:
                return False
            toolchain_data[_PLATFORM] = machine
        else:
            if machine.address is not None:  # else: localhost
                if not (
                    platform_name := LaboratoryAssistant.find_platform_by_address(
                        machine.address
                    )
                ):
                    platform_name = "unnamed_" + "".join(machine.address.split("."))
                    LaboratoryAssistant.add_platform(platform_name, machine)
                toolchain_data[_PLATFORM] = platform_name

        toolchain_data[_TARGET_ARCH] = target_arch.value
        toolchain_data[_ATTRIBUTES] = toolchain.data
        if toolchain.sysroot:
            toolchain_data[_SYSROOT] = toolchain.sysroot

        _toolbox = LaboratoryAssistant.parse_config_file()
        _toolbox[_TOOLCHAINS][toolchain.name] = toolchain_data
        LaboratoryAssistant._dump_config(_toolbox)

        return True

    @staticmethod
    def delete_toolchain(name: str) -> None:
        """Delete toolchain from Amphimixis global config by name.

        :param str name: Name of toolchain
        """
        toolbox = LaboratoryAssistant.parse_config_file()
        toolbox[_TOOLCHAINS].pop(name)
