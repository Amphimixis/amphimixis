"""Module for validating an existing input file."""

# pylint: disable=W0603, C0103

from ipaddress import ip_address
from os import path
from re import compile as re_compile
from typing import Any

import yaml

from amphimixis.core.build_systems import build_systems_dict, runners_dict
from amphimixis.core.general import (
    IUI,
    NULL_UI,
    Arch,
    CompilerFlagsAttrs,
    ToolchainAttrs,
)
from amphimixis.core.laboratory_assistant import LaboratoryAssistant
from amphimixis.core.logger import setup_logger

DEFAULT_PORT = 22

_errors_count = 0

_logger = setup_logger("validator")
_ui: IUI = NULL_UI


def validate(config_file_path: str, ui: IUI = NULL_UI) -> bool:
    """Validate config file.

    :rtype: bool
    :return: Outcome value :

         True if config is valid
         False if config is invalid or file not exists
    """
    global _ui, _errors_count
    _ui = ui
    _errors_count = 0

    if not path.exists(config_file_path):
        _logger.error("Config file not found")
        return False

    with open(config_file_path, encoding="UTF-8") as file:
        input_config = yaml.safe_load(file)

    build_system = input_config.get("build_system")
    if (
        isinstance(build_system, str)
        and str(build_system).lower() not in build_systems_dict
    ):
        _notify_about_error(f"Invalid build_system: {build_system}")

    runner = input_config.get("runner")
    if isinstance(runner, str) and runner.lower() not in runners_dict:
        _notify_about_error(f"Invalid runner: {runner}")

    # validate platforms
    platforms = input_config.get("platforms", {})
    if platforms == {}:
        _notify_about_error("Platforms not found")

    for platform in platforms:
        _is_valid_platform(platform)

    # validate recipes
    recipes = input_config.get("recipes", {})
    if recipes == {}:
        _notify_about_error("Recipes not found")

    for recipe in recipes:
        _is_valid_recipe(recipe)

    # validate builds
    builds = input_config.get("builds", {})
    if builds == {}:
        _notify_about_error("Builds not found")

    for build in builds:
        _is_valid_build(input_config, build)

    _logger.info("Validation completed, errors found: %s", _errors_count)

    return _errors_count == 0


def _is_valid_platform(platform: dict[str, int | str]):
    """Check whether plafrom is valid."""
    pl_id = platform.get("id")
    if not isinstance(pl_id, int | str):
        _notify_about_error(f"Invalid `id` in platform: {pl_id}")

    arch = platform.get("arch")
    if not isinstance(arch, str) or arch.lower() not in Arch:
        supported_archs = ", ".join(arch.value for arch in Arch)
        _notify_about_error(
            f"Invalid arch in platform {pl_id}: {arch}. Supported: {supported_archs}"
        )

    address = platform.get("address")
    if address is not None:
        if not isinstance(address, str) or not _is_valid_address(address):
            _notify_about_error(f"Invalid `address` in platform {pl_id}: {address}")

    username = platform.get("username")
    if not isinstance(username, str) and not (address is None or username is None):
        _notify_about_error(f"Invalid `username` in platform {pl_id}: {username}")

    password = platform.get("password")
    if not isinstance(password, int | str | None):
        _notify_about_error(f"Invalid `password` in platform {pl_id}: {password}")

    port = platform.get("port", DEFAULT_PORT)
    if not isinstance(port, int) or not 1 <= port <= 65535:
        _notify_about_error(f"Invalid `port` in platform {pl_id}: {port}")

    events = platform.get("events")
    if not isinstance(events, list | str | None):
        _notify_about_error(f"Invalid events in platform {pl_id}: {events}")


def _is_valid_recipe(recipe: dict[str, int | str]):
    """Check whether recipe is valid."""
    re_id = recipe.get("id")
    if not isinstance(re_id, int | str):
        _notify_about_error(f"Invalid `id` in recipe: {re_id}")

    config_flags = recipe.get("config_flags")
    if not isinstance(config_flags, str | None):
        _notify_about_error(f"Invalid `config_flags` in recipe {re_id}: {config_flags}")

    compiler_flags = recipe.get("compiler_flags")
    if not isinstance(compiler_flags, dict | None):
        _notify_about_error(
            f"Invalid `compiler_flags` in recipe {re_id}: {compiler_flags}"
        )

    if isinstance(compiler_flags, dict):
        for attr in compiler_flags:
            if not isinstance(attr, str):
                _notify_about_error(
                    f"Recipe {re_id}: invalid `compiler_flags`: invalid attribute `{attr}`"
                )
                continue
            if attr.lower() not in CompilerFlagsAttrs:
                _notify_about_error(
                    f"Recipe {re_id}: invalid `compiler_flags`: unknown attribute `{attr}`"
                )

    toolchain = recipe.get("toolchain")
    _is_valid_toolchain(toolchain)

    sysroot = recipe.get("sysroot")
    if not isinstance(sysroot, str | None):
        _notify_about_error(f"Invalid `sysroot` in build: {sysroot}")

    jobs = recipe.get("jobs")
    if jobs is not None:
        if not isinstance(jobs, int) or jobs <= 0:
            _notify_about_error(
                f"Invalid `jobs` in recipe: `{jobs}` is not positive number"
            )


def _is_valid_build(input_config: dict[str, Any], build: dict[str, int | str]):
    """Check whether build is valid."""
    build_machine_id = build.get("build_machine")
    if (
        not isinstance(build_machine_id, int | str)
        or not _get_by_id(input_config["platforms"], build_machine_id)
        and not LaboratoryAssistant.find_platform(str(build_machine_id))
    ):
        _notify_about_error(f"Invalid `build_machine` in build: {build_machine_id}")

    run_machine_id = build.get("run_machine")
    if (
        not isinstance(run_machine_id, int | str)
        or not _get_by_id(input_config["platforms"], run_machine_id)
        and not LaboratoryAssistant.find_platform(str(run_machine_id))
    ):
        _notify_about_error(f"Invalid `run_machine` in build: {run_machine_id}")

    recipe_id = build.get("recipe_id")
    if not isinstance(recipe_id, int | str) or not _get_by_id(
        input_config["recipes"], recipe_id
    ):
        _notify_about_error(f"Invalid `recipe_id` in build: {recipe_id}")

    executables = build.get("executables")
    if not isinstance(executables, list | None):
        _notify_about_error(f"Invalid `executables` in build: {executables}")


def _is_valid_toolchain(toolchain: Any) -> None:

    if not isinstance(toolchain, dict | str | None):
        _notify_about_error(f"Invalid `toolchain` in build: {toolchain}")

    if isinstance(toolchain, str) and not LaboratoryAssistant.find_toolchain_by_name(
        toolchain
    ):
        _notify_about_error(f"Unknown `toolchain` `{toolchain}`")

    if isinstance(toolchain, dict):
        for attr, value in toolchain.items():
            value = str(value)
            if not isinstance(attr, str):
                _notify_about_error(f"Invalid `toolchain`: invalid attribute `{attr}`")
                continue
            if attr.lower() in ToolchainAttrs:
                if not path.isabs(value):
                    _notify_about_error(
                        f"Invalid `toolchain`: {attr}: path `{value}` is not absolute"
                    )
            elif attr.lower() not in CompilerFlagsAttrs and attr != "sysroot":
                _notify_about_error(f"Invalid `toolchain`: unknown attribute `{attr}`")


def _is_valid_address(address: str) -> bool:
    """Check whether address is valid.

    :rtype: bool
    :return: Outcome value :

         True if address is valid
         False if address is invalid
    """
    try:
        ip_address(address)
        return True
    except ValueError:
        if all(part.isdigit() for part in address.rstrip(".").split(".")):
            return False

        # this string checks whether domain name is valid, here some rules:
        # 1. Length <= 253
        # 2. Separate part length <= 63
        # 3. Contains only letters, digits and dash
        # 4. Doesn't start or end with dash
        # 5. May have dot at the end
        hostname_pattern = re_compile(
            r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
            r"(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$"
        )
        return bool(hostname_pattern.match(address))


def _get_by_id(
    items: list[dict[str, str | int]], target_id: int | str
) -> dict[str, str | int]:
    """Find item in dict by id."""
    for item in items:
        if "id" not in item:
            msg = f"Item {item} don't have `id` field"
            _logger.fatal(msg)
            _notify_about_error(msg)
            return {}
        id_ = item["id"]
        if not isinstance(id_, int | str):
            msg = f"Not integer or string id `{id_}` of item {item}"
            _logger.fatal(msg)
            _notify_about_error(msg)
            return {}
        if id_ == target_id:
            return item

    msg = "Item id didn't match any existed id, check input file"
    _logger.error(msg)
    _notify_about_error(msg)
    return {}


# pylint: disable=global-variable-not-assigned
def _notify_about_error(msg: str) -> None:
    """Handle messages due to invalid fields in config."""
    global _errors_count
    global _ui
    _errors_count += 1
    _logger.error(msg)
    _ui.send_error("Config", msg)
