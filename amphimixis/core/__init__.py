"""Core module that contains director with main API and modules that he uses."""

from amphimixis.core import general
from amphimixis.core.analyzer import analyze
from amphimixis.core.build_systems import build_systems_dict
from amphimixis.core.builder import Builder
from amphimixis.core.configurator import (
    cleanup_qemu_machines,
    create_flags,
    create_machine,
    create_toolchain,
    parse_config,
)
from amphimixis.core.laboratory_assistant import LaboratoryAssistant
from amphimixis.core.profiler import Profiler
from amphimixis.core.shell import Shell
from amphimixis.core.validator import validate

# pylint: disable=duplicate-code
__all__ = [
    "general",
    "build_systems_dict",
    "analyze",
    "cleanup_qemu_machines",
    "create_flags",
    "create_machine",
    "create_toolchain",
    "parse_config",
    "Builder",
    "Profiler",
    "Shell",
    "LaboratoryAssistant",
    "validate",
]
