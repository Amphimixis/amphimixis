"""Module for configuring a new build."""

import pickle
from os import path
from pathlib import Path
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
from amphimixis.core.qemu_machine import QemuMachineProvisioner
from amphimixis.core.shell import Shell
from amphimixis.core.validator import DEFAULT_PORT, validate

_logger = setup_logger("configurator")
INVITING_NAME = "Config"

_qemu_provisioners: dict[int, QemuMachineProvisioner] = {}


def provision_qemu_machines(input_config: dict[str, Any], ui: IUI = NULL_UI) -> bool:
    """Provision QEMU machines for platforms that have qemu config.

    Required packages are installed only on auto-downloaded default
    images; platforms with custom VM files are used as-is.

    :param dict input_config: Parsed input configuration.
    :param IUI ui: User interface for progress display.
    :return bool: True if all qemu platforms were provisioned, False otherwise.
    """
    for platform in input_config.get("platforms", []):
        qemu_info = platform.get("qemu")
        if not qemu_info:
            continue

        pl_id = platform.get("id")
        if pl_id is None:
            continue
        pl_id = int(pl_id)
        arch = str(platform.get("arch") or "unknown")

        ui.update_message("QEMU", f"Provisioning {arch} VM for platform {pl_id}...")

        provisioner: QemuMachineProvisioner | None = None
        try:
            machine = create_machine(platform)
            provisioner = QemuMachineProvisioner(machine, ui)
            provisioner.start()

            build_system = input_config.get("build_system", "cmake")
            runner = input_config.get("runner", "make")
            if provisioner.uses_default_files:
                packages = _get_required_packages(
                    provisioner.is_default_image, build_system, runner
                )
                if packages:
                    provisioner.install_packages(packages)
            else:
                _logger.info(
                    "Skipping package installation for platform %s: "
                    "custom VM files, required tools must be pre-installed",
                    pl_id,
                )
                ui.update_message(
                    "QEMU",
                    f"Platform {pl_id}: custom image, "
                    "skipping package installation...",
                )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _logger.error("Failed to provision qemu VM for platform %s: %s", pl_id, exc)
            ui.mark_failed(
                error_message=f"Failed to provision qemu VM for platform {pl_id}"
            )
            if provisioner is not None:
                provisioner.stop()
            for _, started in _qemu_provisioners.items():
                started.stop()
            _qemu_provisioners.clear()
            return False

        assert provisioner is not None
        _qemu_provisioners[pl_id] = provisioner

    return True


def _get_required_packages(
    default_image: bool,
    build_system: str,
    runner: str,
) -> list[str]:
    """Determine required packages based on build_system and runner.

    :param bool default_image: Value for choosing package names
        (apk names for the default image, apt names otherwise).
    :param str build_system: Build system (e.g., "cmake", "make", "ninja").
    :param str runner: Runner (e.g., "make", "ninja").
    :return: List of package names to install.
    """
    if default_image:
        packages = ["g++", "util-linux", "perf", "rsync"]
    else:
        packages = ["g++", "time", "linux-perf", "rsync"]

    packages.insert(0, "bash")

    build_system_lower = str(build_system).lower()
    runner_lower = str(runner).lower()

    if build_system_lower == "cmake":
        packages.append("cmake")

    if runner_lower == "make":
        packages.append("make")
    elif runner_lower == "ninja":
        packages.append("ninja-build")

    return packages


def cleanup_qemu_machines() -> None:
    """Stop all provisioned QEMU machines that are not marked keep_alive."""
    for pl_id, provisioner in _qemu_provisioners.items():
        if provisioner.keep_alive:
            _logger.info(
                "Keeping QEMU VM for platform %s alive (keep_alive=true)", pl_id
            )
            continue
        _logger.info("Stopping QEMU VM for platform %s", pl_id)
        provisioner.stop()
    _qemu_provisioners.clear()


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

    if not provision_qemu_machines(input_config, ui):
        _logger.error("Failed to provision qemu machines")
        ui.mark_failed("Failed to provision qemu machines")
        return False

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


def _create_build(  # pylint: disable=R0913,R0914,R0917
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
    if dict_from_input := _get_by_id(input_config["platforms"], build_machine_id):
        build_machine = create_machine(dict_from_input)
    elif machine_from_la := LaboratoryAssistant.find_platform(build_machine_id):
        build_machine = machine_from_la
    else:
        msg = f"Build '{build_name}': unknown build machine: '{build_machine_id}'"
        _logger.fatal(msg)
        raise ValueError(msg)

    run_machine: MachineInfo
    if dict_from_input := _get_by_id(input_config["platforms"], run_machine_id):
        run_machine = create_machine(dict_from_input)
    elif machine_from_la := LaboratoryAssistant.find_platform(run_machine_id):
        run_machine = machine_from_la
    else:
        msg = f"Build '{build_name}': unknown run machine: '{run_machine_id}'"
        _logger.fatal(msg)
        raise ValueError(msg)

    recipe_info = _get_by_id(input_config["recipes"], recipe_id)

    if not _has_valid_arch(project, run_machine, ui):
        return False

    toolchain = None
    if toolchain_info := recipe_info.get("toolchain"):
        toolchain = create_toolchain(toolchain_info)

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


def _generate_build_name(build_id: str, run_id: str, recipe_id: str) -> str:
    """Generate a build path based on build, run, and recipe IDs."""
    return f"{build_id}_{run_id}_{recipe_id}"


def _get_by_id(
    items: list[dict[str, str | int]], target_id: str
) -> dict[str, str | int]:
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
    """Check whether run machine arch is valid."""
    qemu_enabled = machine.qemu is not None
    if machine.address is None and not qemu_enabled:
        if machine.arch.lower() not in local_arch().lower():
            _logger.error(
                "Invalid local machine arch: %s, your machine is %s",
                machine.arch.name.lower(),
                local_arch().lower(),
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
        _logger.error(
            "Invalid remote machine arch: %s, remote machine is %s",
            machine.arch.name.lower(),
            remote_arch.lower(),
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
    if build_system in build_systems_dict:
        return build_system

    return None


def create_machine(machine_info: dict[str, Any]) -> general.MachineInfo:
    """Create a new machine.

    For qemu platforms the address is forced to 127.0.0.1 and
    auto-downloaded images always use root/root credentials.
    Custom VM files require explicit username and password.

    :param dict machine_info: Platform dictionary from the input config.
    :return: MachineInfo with arch, address, auth and qemu config.
    """
    arch = str(machine_info.get("arch"))
    address = machine_info.get("address")
    address = str(address) if address is not None else None

    qemu_info = machine_info.get("qemu")
    qemu = None
    auth = None
    username: str | None
    password: str | None

    if qemu_info is not None and qemu_info:
        # qemu works with localhost (127.0.0.1); validated upstream
        address = "127.0.0.1"

        port = int(machine_info.get("port", DEFAULT_PORT))

        files_provided = isinstance(qemu_info, dict) and any(
            qemu_info.get(key) for key in ("kernel", "initrd", "disk_image")
        )

        if files_provided and (
            not machine_info.get("username") or machine_info.get("password") is None
        ):
            raise ValueError(
                "Username and password are required when qemu is enabled "
                "with custom files (kernel/initrd/disk_image)."
            )

        username = str(machine_info.get("username") or "root")
        password = str(machine_info.get("password") or "root")

        if not files_provided and (username != "root" or password != "root"):
            _logger.warning(
                "Default QEMU images only support 'root/root' credentials; "
                "ignoring provided '%s/%s'.",
                username,
                password,
            )
            username, password = "root", "root"

        auth = general.MachineAuthenticationInfo(username, password, port)

        if isinstance(qemu_info, bool):
            qemu = general.QemuConfig()
        elif isinstance(qemu_info, dict):
            qemu = create_qemu_config(qemu_info)
        else:
            raise ValueError(
                f"Invalid qemu value: {qemu_info}. Use true or a dict with qemu options."
            )
    else:
        if address is not None:
            username = str(machine_info.get("username"))
            raw_password = machine_info.get("password")
            password = str(raw_password) if raw_password is not None else None
            port = int(machine_info.get("port", DEFAULT_PORT))

            if username is not None:
                auth = general.MachineAuthenticationInfo(str(username), password, port)

    machine = general.MachineInfo(general.Arch(arch.lower()), address, auth, qemu)

    return machine


def create_qemu_config(qemu_info: Any) -> general.QemuConfig:
    """Create QEMU configuration.

    :param dict qemu_info: Dictionary with QEMU configuration options.
    :return: QemuConfig instance.
    """
    kernel = qemu_info.get("kernel")
    initrd = qemu_info.get("initrd")
    disk_image = qemu_info.get("disk_image")
    raw_extra = qemu_info.get("extra_args") or []
    if not isinstance(raw_extra, list):
        raise ValueError(
            f"Invalid qemu extra_args: {raw_extra!r}. Expected list of strings."
        )

    return general.QemuConfig(
        machine=str(qemu_info["machine"]) if qemu_info.get("machine") else None,
        cpu=str(qemu_info.get("cpu")) if qemu_info.get("cpu") else None,
        memory=int(qemu_info.get("memory", 4)),
        smp=int(qemu_info.get("smp", 4)),
        kernel=Path(str(kernel)) if kernel else None,
        initrd=Path(str(initrd)) if initrd else None,
        disk_image=Path(str(disk_image)) if disk_image else None,
        keep_alive=bool(qemu_info.get("keep_alive", False)),
        extra_args=list(map(str, raw_extra)),
    )


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
