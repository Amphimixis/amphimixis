"""Module containing dictionary of build systems and implementations of build systems."""

from amphimixis.core.build_systems.autoconf import Autoconf
from amphimixis.core.build_systems.build_systems import build_systems_dict, runners_dict
from amphimixis.core.build_systems.cmake import CMake
from amphimixis.core.build_systems.make import Make
from amphimixis.core.build_systems.ninja import Ninja

__all__ = [
    "build_systems_dict",
    "runners_dict",
    "Autoconf",
    "CMake",
    "Make",
    "Ninja",
]
