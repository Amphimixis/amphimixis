"""Module for configuring a new build."""

import pickle
from os import path
from platform import machine as local_arch
from typing import Any, SupportsInt

import yaml

from amphimixis.core.build_systems import build_systems_dict, runners_dict
from amphimixis.core.general import (
    DUMMY_RUNNER,
    IUI,
    NULL_UI,
    MachineInfo,
    general,
    tools,
)
from amphimixis.core.general.constants import ANALYZED_FILE_NAME
from amphimixis.core.laboratory_assistant import LaboratoryAssistant
from amphimixis.core.logger import setup_logger
from amphimixis.core.shell import Shell
from amphimixis.core.validator import validate

DEFAULT_PORT = 22

_logger = setup_logger("configurator")
INVITING_NAME = "Config"


# pylint: disable=too-many-return-statements
def parse_config(
    project: general.Project, config_file_path: str, ui: IUI = NULL_UI
) -> bool:
    """Configure builds.

    :rtype: bool
    :return: Outcome value :

         True if configuration succeeded
         False if configuration failed
    """
    ui.update_message(INVITING_NAME, "Parsing configuration file...")

    if not path.exists(project.path):
        _logger.error("Incorrect project path @_@, check input arguments")
        ui.mark_failed("Project path not found")
        return False

    project.builds = []

    if not path.exists(config_file_path):
        _logger.error("Input file path not exists")
        ui.mark_failed("Input file path not exists")
        return False

    if not validate(config_file_path, ui):
        _logger.error("Incorrect input file")
        ui.mark_failed("Incorrect input file", build_id=INVITING_NAME)
        return False

    with open(config_file_path, encoding="UTF-8") as file:
        input_config = yaml.safe_load(file)

    build_system: str | None = str(input_config.get("build_system")).lower()
    if build_system not in build_systems_dict:
        if not (build_system := _get_analyzed_build_system()):
            _logger.error("Did not find any proper build_system")
            ui.mark_failed("No build system found", build_id=INVITING_NAME)
            return False
    runner_name = str(input_config.get("runner", None)).lower()
    if (
        runner_name
        and runner_name in runners_dict
        and runners_dict[runner_name] in build_systems_dict[build_system][1]
    ):
        runner = runners_dict[runner_name](project, ui)
    elif len(build_systems_dict[build_system][1]) > 0:
        runner = build_systems_dict[build_system][1][0](project, ui)
    else:  # if build system doesn't have runners (like Make)
        runner = DUMMY_RUNNER
    project.build_system = build_systems_dict[build_system][0](project, runner, ui)

    for build in input_config["builds"]:
        if not _create_build(
            project,
            input_config,
            build,
            ui,
        ):
            ui.mark_failed("Failed to create build", build_id=INVITING_NAME)
            return False

    config_path = tools.project_name(project) + ".project"
    with open(config_path, "wb") as file:
        pickle.dump(project, file)

    _logger.info("Configuration completed successfully!")
    return True


def _create_build(  # pylint: disable=too-many-branches, too-many-arguments, too-many-locals, too-many-statements, too-many-positional-arguments
    project: general.Project,
    input_config: dict[str, Any],
    build_dict: dict[str, Any],
    ui: IUI = NULL_UI,
) -> bool:
    """Create a new build and save its configuration to a Pickle file."""
    build_machine_id = str(build_dict["build_machine"])
    run_machine_id = str(build_dict["run_machine"])
    recipe_id = str(build_dict["recipe_id"])
    executables = build_dict.get("executables", [])

    build_name = _generate_build_name(
        build_dict["build_machine"], build_dict["run_machine"], build_dict["recipe_id"]
    )

    build_machine: MachineInfo
    if machine_from_la := LaboratoryAssistant.find_platform(build_machine_id):
        build_machine = machine_from_la
        if dict_from_input := _get_by_id(
            input_config["platforms"], f"@{build_machine_id}"
        ):
            _apply_platform_overrides(build_machine, dict_from_input)
    elif dict_from_input := _get_by_id(input_config["platforms"], build_machine_id):
        build_machine = create_machine(dict_from_input)
    else:
        msg = f"Build '{build_name}': unknown build machine: '{build_machine_id}'"
        _logger.fatal(msg)
        raise ValueError(msg)

    run_machine: MachineInfo
    if machine_from_la := LaboratoryAssistant.find_platform(run_machine_id):
        run_machine = machine_from_la
        if dict_from_input := _get_by_id(
            input_config["platforms"], f"@{run_machine_id}"
        ):
            _apply_platform_overrides(run_machine, dict_from_input)
    elif dict_from_input := _get_by_id(input_config["platforms"], run_machine_id):
        run_machine = create_machine(dict_from_input)
    else:
        msg = f"Build '{build_name}': unknown run machine: '{run_machine_id}'"
        _logger.fatal(msg)
        raise ValueError(msg)

    recipe_info = _get_by_id(input_config["recipes"], recipe_id)

    if not _has_valid_arch(project, run_machine, ui):
        return False

    toolchain = None
    if toolchain_info := recipe_info.get("toolchain"):
        toolchain = create_toolchain(toolchain_info)  # type: ignore[arg-type]

    sysroot = recipe_info.get("sysroot")
    if sysroot is None and toolchain is not None:
        sysroot = toolchain.sysroot

    config_flags = recipe_info.get("config_flags")
    compiler_flags = create_flags(recipe_info.get("compiler_flags"))  # type: ignore
    jobs = recipe_info.get("jobs")
    if not isinstance(jobs, SupportsInt | None):
        msg = f"Build '{build_name}': invalid jobs: '{jobs}'"
        _logger.fatal(msg)
        raise ValueError(msg)

    build = general.Build(
        build_machine,
        run_machine,
        build_name,
        executables,
        toolchain,
        str(sysroot) if sysroot else None,
        compiler_flags,
        str(config_flags) if config_flags else None,
        int(jobs) if jobs else None,
    )

    project.builds.append(build)

    return True


def _apply_platform_overrides(
    machine: MachineInfo,
    platform_cfg: dict[str, int | str | list[str]],
) -> None:
    """Temporary override some global machine info by local info.

    :param str machine: Machine from global config
    :param dict[str, int | str] platform_cfg: Info from local config
    :rtype: None
    """
    arch = platform_cfg.get("arch")
    if arch:
        machine.arch = general.Arch(str(arch).lower())

    events = platform_cfg.get("events")
    if events:
        machine.events = events.split() if isinstance(events, str) else events  # type: ignore[assignment] #pylint: disable=line-too-long

    address = platform_cfg.get("address")
    username = platform_cfg.get("username")
    password = platform_cfg.get("password")
    port = platform_cfg.get("port")

    if machine.auth:
        if username:
            machine.auth.username = str(username)
        if password:
            machine.auth.password = str(password)
        if port:
            machine.auth.port = int(port)  # type: ignore[arg-type]
    elif username and port:
        machine.auth = general.MachineAuthenticationInfo(
            str(username),
            str(password) if password else None,
            int(port),  # type: ignore[arg-type]
        )
    elif password:
        msg = "Can't assign password without auth info"
        _logger.fatal(msg)
        raise ValueError(msg)

    if address and machine.auth:
        machine.address = str(address)
    elif address:
        msg = "Can't assign address without auth info"
        _logger.fatal(msg)
        raise ValueError(msg)


def _generate_build_name(build_id: str, run_id: str, recipe_id: str) -> str:
    """Generate a build path based on build, run, and recipe IDs."""
    return f"{build_id}_{run_id}_{recipe_id}"


def _get_by_id(
    items: list[dict[str, str | int | list[str]]], target_id: str
) -> dict[str, str | int | list[str]]:
    """Find an item in a dictionary by ID."""
    for item in items:
        id_ = str(item["id"])
        if id_ == target_id:
            return item

    _logger.error("Item id didn't match any existed id, check input file")
    return {}


def _has_valid_arch(
    project: general.Project, machine: general.MachineInfo, ui: IUI = NULL_UI
) -> bool:
    """Check whether the run machine architecture is valid."""
    if machine.address is None:
        if machine.arch.lower() not in local_arch().lower():
            supported_archs = ", ".join(arch.value for arch in general.Arch)
            _logger.error(
                "Invalid local machine arch: %s, your machine is %s. Supported: %s",
                machine.arch.name.lower(),
                local_arch().lower(),
                supported_archs,
            )
            ui.mark_failed(
                f"Config: invalid local architecture. Supported: {supported_archs}"
            )
            return False
        return True

    # remote case
    ui.update_message(INVITING_NAME, "Checking remote architecture for validity...")
    shell = Shell(project, machine, ui).connect()
    error_code, stdout, _ = shell.run("uname -m")
    if error_code != 0:
        _logger.error(
            "An error occured during reading remote machine arch, check remote machine"
        )
        ui.mark_failed("Failed to check remote architecture", build_id=INVITING_NAME)
        return False

    remote_arch = stdout[0][0]
    if machine.arch.lower() not in remote_arch.lower():
        supported_archs = ", ".join(arch.value for arch in general.Arch)
        _logger.error(
            "Invalid remote machine arch: %s, remote machine is %s. Supported: %s",
            machine.arch.name.lower(),
            remote_arch.lower(),
            supported_archs,
        )
        ui.mark_failed(
            f"Config: invalid remote architecture. Supported: {supported_archs}"
        )
        ui.mark_failed("Invalid remote architecture", build_id=INVITING_NAME)
        return False

    return True


def _get_analyzed_build_system() -> str | None:
    """Get the build system from the analyzed project.

    :rtype: str | None
    :return: Outcome value :

         Build system name if it was found
         None if build system was not found or
         analysis was not completed
    """
    if not path.exists(ANALYZED_FILE_NAME):
        _logger.warning("Analyzer output file not found")
        return None

    with open(ANALYZED_FILE_NAME, encoding="UTF-8") as file:
        analyzed = yaml.safe_load(file)

    if not analyzed:
        return None

    if not isinstance(analyzed, dict):
        raise TypeError("Incorrect analyzer output file")

    if "build_systems" not in analyzed:
        raise TypeError("Missing 'build_systems' key in analyzer output file")

    build_systems = analyzed["build_systems"]
    if not isinstance(build_systems, list) or not build_systems:
        raise TypeError("'Build_systems' must be a non-empty list")

    if not isinstance(build_systems[0], str):
        raise TypeError("Incorrect build systems list")

    build_system = build_systems[0].lower()
    if (
        build_system in build_systems_dict
    ):  # take first (in priority) found build system
        return build_system

    return None


def create_machine(
    machine_info: dict[str, int | str | list[str]],
) -> general.MachineInfo:
    """Create a new machine."""
    auth = None
    arch = str(machine_info.get("arch"))
    address = machine_info.get("address")
    address = str(address) if address is not None else None
    events = machine_info.get("events")
    events = (events.split() if isinstance(events, str) else events) or None

    if address is not None:
        username = str(machine_info.get("username"))
        password = machine_info.get("password")
        password = str(password) if password is not None else None
        port = int(machine_info.get("port", DEFAULT_PORT))  # type: ignore[arg-type]

        auth = general.MachineAuthenticationInfo(username, password, port)

    machine = general.MachineInfo(general.Arch(arch.lower()), address, auth, events)  # type: ignore[arg-type] # pylint: disable=line-too-long

    return machine


def create_toolchain(
    toolchain_dict: dict[str, str | int] | str | int,
) -> general.Toolchain | None:
    """Create a new toolchain."""
    if isinstance(toolchain_dict, str | int):
        return LaboratoryAssistant.find_toolchain_by_name(str(toolchain_dict))

    name = toolchain_dict.get("name")
    if not name:
        return None

    toolchain = general.Toolchain(str(name))
    for attr in toolchain_dict:
        if attr.lower() in general.ToolchainAttrs:
            toolchain.set(
                general.ToolchainAttrs(attr.lower()), str(toolchain_dict[attr])
            )

        elif attr.lower() in general.CompilerFlagsAttrs:
            toolchain.set(
                general.CompilerFlagsAttrs(attr.lower()), str(toolchain_dict[attr])
            )

        elif attr.lower() == "sysroot":
            toolchain.sysroot = str(toolchain_dict[attr])

        else:
            _logger.info("Unknown toolchain attribute: %s, skipping...", attr.lower())

    return toolchain


def create_flags(
    compiler_flags_dict: dict[str, str] | None,
) -> general.CompilerFlags | None:
    """Create new compiler flags."""
    if compiler_flags_dict is None:
        return None

    compiler_flags = general.CompilerFlags()
    for key, value in compiler_flags_dict.items():
        flag = key.lower()
        if flag not in general.CompilerFlagsAttrs:
            _logger.info(
                "Unknown compiler flag attribute: %s, skipping...", flag.lower()
            )
            continue

        compiler_flags.set(general.CompilerFlagsAttrs(flag), value)

    return compiler_flags
