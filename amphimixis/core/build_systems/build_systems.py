"""Define mappings for build systems and runners.

Contain dictionaries mapping names to corresponding
IHighLevelBuildSystem and ILowLevelBuildSystem implementations.
"""

from amphimixis.core.build_systems.autoconf import Autoconf
from amphimixis.core.build_systems.cmake import CMake
from amphimixis.core.build_systems.make import Make
from amphimixis.core.build_systems.ninja import Ninja
from amphimixis.core.general.general import IHighLevelBuildSystem, ILowLevelBuildSystem

# First element -- class of matched build system,
# other are runners for this build system in priority
build_systems_dict: dict[
    str, tuple[type[IHighLevelBuildSystem], list[type[ILowLevelBuildSystem]]]
] = {
    "autoconf": (Autoconf, [Make]),
    "cmake": (CMake, [Ninja, Make]),
    "make": (Make, []),
}

runners_dict: dict[str, type[ILowLevelBuildSystem]] = {
    "make": Make,
    "ninja": Ninja,
}
