"""Add toolchain command."""

# pylint: disable=duplicate-code

import os

import yaml

from amphimixis.amixis.templates import TOOLCHAIN_TEMPLATE
from amphimixis.amixis.utils import (
    create_temp_file,
    get_content_with_editor,
    prompt_continue,
)
from amphimixis.core.configurator import create_toolchain
from amphimixis.core.general.general import Arch, MachineInfo
from amphimixis.core.laboratory_assistant import LaboratoryAssistant


# pylint: disable=too-many-branches, too-many-statements
def run_add_toolchain() -> bool:
    """Interactively add a toolchain to global config.

    Opens an editor with a toolchain template, validates user input,
    checks for duplicates, ensures platform exists (creates if missing),
    and saves the toolchain using LaboratoryAssistant API.

    :return: True if toolchain added successfully, False otherwise.
    :rtype: bool
    """
    editor = os.environ.get("EDITOR", "nano")
    current_content = TOOLCHAIN_TEMPLATE

    print(f"Opening editor: {editor}")
    print("Edit the toolchain template and save to validate.")
    print("The editor will reopen if validation fails.\n")

    temp_path = create_temp_file(current_content)
    try:
        while True:
            new_content = get_content_with_editor(editor, temp_path)
            if new_content is None:
                if not prompt_continue():
                    return False
                continue

            current_content = new_content
            data = _validate_toolchain_yaml(current_content)
            if data is None:
                if not prompt_continue():
                    return False
                continue

            name = _get_name(data)
            if name is None:
                if not prompt_continue():
                    return False
                continue

            if _check_toolchain_exists(name):
                if not prompt_continue():
                    return False
                continue

            target_arch_str = _get_target_arch_str(data)
            if target_arch_str is None:
                if not prompt_continue():
                    return False
                continue

            try:
                target_arch = Arch(target_arch_str.lower())
            except ValueError:
                print(f"Error: Unsupported architecture '{target_arch_str}'.")
                if not prompt_continue():
                    return False
                continue

            platform = _get_platform(data)
            if platform is None:
                if not prompt_continue():
                    return False
                continue

            if not LaboratoryAssistant.find_platform(platform):
                print(f"Platform '{platform}' not found. Creating as local platform...")
                machine = MachineInfo(target_arch, address=None, auth=None, events=None)
                if not LaboratoryAssistant.add_platform(platform, machine):
                    print(f"Failed to create platform '{platform}'.")
                    if not prompt_continue():
                        return False
                    continue
                print(f"Platform '{platform}' created successfully.")

            try:
                toolchain = create_toolchain(data)
            except ValueError as e:
                print(f"Error: {e}")
                if not prompt_continue():
                    return False
                continue

            if toolchain is None:
                print(
                    "Error: Failed to create toolchain object. Check your toolchain fields."
                )
                if not prompt_continue():
                    return False
                continue

            if LaboratoryAssistant.add_toolchain(toolchain, platform, target_arch):
                print(f"Toolchain '{name}' added successfully!")
                return True
            print(f"Failed to add toolchain '{name}'.")
            if not prompt_continue():
                return False
            continue
    finally:
        if temp_path.exists():
            os.unlink(temp_path)


def _validate_toolchain_yaml(content: str) -> None | dict:
    """Validate toolchain YAML content.

    :param str content: YAML content to validate
    :return: Dictionary if valid, None otherwise
    :rtype: None | dict
    """
    try:
        toolchain = yaml.safe_load(content)
    except yaml.YAMLError as e:
        print(f"\nYAML parse error: {e}")
        print("Editor will reopen for corrections...")
        return None

    if not isinstance(toolchain, dict):
        print("\nError: Toolchain must be a dictionary.")
        print("Editor will reopen for corrections...")
        return None

    if "name" not in toolchain or not toolchain["name"]:
        print("\nError: Toolchain must have a 'name' field.")
        print("Editor will reopen for corrections...")
        return None

    return toolchain


def _check_toolchain_exists(toolchain_name: str) -> bool:
    """Check if toolchain with given name already exists.

    :param str toolchain_name: Name of the toolchain
    :return: True if exists, False otherwise
    :rtype: bool
    """
    if LaboratoryAssistant.find_toolchain_by_name(toolchain_name) is not None:
        print(f"\nWarning: Toolchain '{toolchain_name}' already exists.")
        print("Not overwriting. Please choose a different name.")
        print("Editor will reopen for corrections...")
        return True
    return False


def _get_name(data: dict) -> str | None:
    """Extract and validate 'name' field from toolchain data.

    :param dict data: Dictionary containing toolchain configuration
    :return: Validated name string, or None if invalid
    :rtype: str | None
    """
    name = data.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        print("Error: 'name' field is required and must be a non-empty string.")
        return None
    return name


def _get_target_arch_str(data: dict) -> str | None:
    """Extract and validate 'target_arch' field from toolchain data.

    :param dict data: Dictionary containing toolchain configuration
    :return: Validated target architecture string, or None if missing
    :rtype: str | None
    """
    target_arch = data.get("target_arch")
    if not target_arch:
        print("Error: 'target_arch' field is required.")
        return None
    return target_arch


def _get_platform(data: dict) -> str | None:
    """Extract and validate 'platform' field from toolchain data.

    :param dict data: Dictionary containing toolchain configuration
    :return: Validated platform name string, or None if missing
    :rtype: str | None
    """
    platform = data.get("platform")
    if not platform:
        print("Error: 'platform' field is required.")
        return None
    return platform
