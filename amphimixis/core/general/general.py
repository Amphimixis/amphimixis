"""The common module that is used in most other modules."""

import os
import queue
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from os.path import isabs


class Arch(StrEnum):
    """Supported architectures."""

    X86 = "x86"
    RISCV = "riscv"
    ARM = "arm"


# pylint: disable=too-many-instance-attributes
@dataclass
class ProfileStats:
    """Profiling and execution statistics for an executable.

    :var str | None build_name: Name of the build.
    :var str | None executable: Path to the executable file (relative to build dir).
    :var bool | None executable_run_success: Whether the executable finished successfully.
    :var str | None real_time: Wall-clock (real) execution time.
    :var str | None user_time: CPU time spent in user mode.
    :var str | None kernel_time: CPU time spent in kernel mode.
    :var str | None perf_stat: Output of `perf stat` command.
    :var str | None perf_record_name: Filename of the recorded `perf record` data.
    :var str | None perf_script_name: Filename of the processed `perf script` output.
    :var str | None perf_archive_name: Filename of the archive gathered using `perf archive`.
    """

    build_name: str | None = None
    executable: str | None = None
    executable_run_success: bool | None = None
    real_time: str | None = None
    user_time: str | None = None
    kernel_time: str | None = None
    perf_stat: str | None = None
    perf_record_name: str | None = None
    perf_script_name: str | None = None
    perf_archive_name: str | None = None


ProjectStats = dict[str, dict[str, ProfileStats]]


@dataclass
class MachineAuthenticationInfo:
    """Information about authentication on a remote machine.

    :var str username: Username for authentication.
    :var str | None password: Password for authentication.
        Can be set to None if an SSH agent is used.
    :var int port: Port number for the SSH connection.
    """

    username: str
    password: str | None
    port: int

    @property
    def __dictstr__(self) -> dict[str, str]:
        """Return a dictionary representation with string-serializable values."""
        ret = {"username": self.username}
        if self.password is not None:
            ret["password"] = self.password
        ret["port"] = str(self.port)
        return ret


@dataclass
class MachineInfo:
    """Information about the machine.

    :var Arch arch: Architecture of the machine.
    :var str | None address: IP address or hostname of the remote machine.
        If address is None, the machine is considered to be local.
    :var MachineAuthenticationInfo auth: Authentication info for the machine.
    """

    arch: Arch
    address: str | None
    auth: MachineAuthenticationInfo | None

    @property
    def __dictstr__(self) -> dict:
        """Return a dictionary representation with string-serializable values."""
        ret: dict[str, str | dict] = {"arch": self.arch.value}
        if self.address is not None:
            ret["address"] = self.address
        if self.auth is not None:
            ret["auth"] = self.auth.__dictstr__
        return ret


# pylint: disable = too-many-instance-attributes
class CompilerFlagsAttrs(StrEnum):
    """Enumeration for getting access to flags of concrete compiler."""

    C_FLAGS = "c_flags"
    CXX_FLAGS = "cxx_flags"
    CSHARP_FLAGS = "csharp_flags"
    CUDA_FLAGS = "cuda_flags"
    OBJC_FLAGS = "objc_flags"
    OBJCXX_FLAGS = "objcxx_flags"
    FORTRAN_FLAGS = "fortran_flags"
    HIP_FLAGS = "hip_flags"
    ISPC_FLAGS = "ispc_flags"
    SWIFT_FLAGS = "swift_flags"
    ASM_FLAGS = "asm_flags"
    ASM_NASM_FLAGS = "asm_nasm_flags"
    ASM_MARMASM_FLAGS = "asm_marmasm_flags"
    ASM_MASM_FLAGS = "asm_masm_flags"
    ASM_ATT_FLAGS = "asm_att_flags"


# pylint: disable = too-many-instance-attributes
class ToolchainAttrs(StrEnum):
    """Constants for getting access to attributes from toolchain dictionary."""

    # TOOLS: postfix "_t" means "tool"
    AR_T = "ar"
    AS_T = "as"
    LD_T = "ld"
    NM_T = "nm"
    OBJCOPY_T = "objcopy"
    OBJDUMP_T = "objdump"
    RANLIB_T = "ranlib"
    READELF_T = "readelf"
    STRIP_T = "strip"

    # COMPILERS
    C_COMPILER = "c_compiler"
    CXX_COMPILER = "cxx_compiler"
    CSHARP_COMPILER = "csharp_compiler"
    CUDA_COMPILER = "cuda_compiler"
    OBJC_COMPILER = "objc_compiler"
    OBJCXX_COMPILER = "objcxx_compiler"
    FORTRAN_COMPILER = "fortran_compiler"
    HIP_COMPILER = "hip_compiler"
    ISPC_COMPILER = "ispc_compiler"
    SWIFT_COMPILER = "swift_compiler"
    ASM_COMPILER = "asm_compiler"
    ASM_NASM_COMPILER = "asm_nasm_compiler"
    ASM_MARMASM_COMPILER = "asm_marmasm_compiler"
    ASM_MASM_COMPILER = "asm_masm_compiler"
    ASM_ATT_COMPILER = "asm_att_compiler"


class Toolchain:
    """Class that generalized idea of toolchain."""

    def __init__(self, name: str | None = None, sysroot: str | None = None):
        # attr -> [ /path/to/any | compiler_defualt_flags ]
        self.__attrs: dict[str, str] = {}
        self.__name = name
        self.sysroot = sysroot

    @property
    def name(self) -> str | None:
        """Name of toolchain getter."""
        return self.__name

    @property
    def sysroot(self) -> str | None:
        """Sysroot of toolchain getter."""
        return self.__sysroot

    @sysroot.setter
    def sysroot(self, new_path: None | str) -> None:
        """Sysroot of toolchain setter."""
        if new_path is None or isabs(new_path):
            self.__sysroot = new_path
        else:
            raise ValueError(
                f"Setting sysroot to toolchain error: path '{new_path}' is not absolute"
            )

    def get(self, attr: ToolchainAttrs | CompilerFlagsAttrs) -> str | None:
        """Getter of toolchain attributes."""
        return self.__attrs.get(attr.value)

    def set(self, attr: ToolchainAttrs | CompilerFlagsAttrs, new_value: str) -> None:
        """Setter of toolchain attributes.

        :param ToolchainAttrs | CompilerFlagsAttrs attr: Tool / compiler / flags
            attribute of toolchain
        :param str new_value: absolute path to tool / compiler or flags of compiler
        """
        if isinstance(attr, ToolchainAttrs) and not isabs(new_value):
            raise ValueError(
                f"Setting {attr.value} to toolchain error: path '{new_value}' is not absolute"
            )
        self.__attrs[attr.value] = new_value

    @property
    def data(self) -> dict[str, str]:
        """Return dictionary with all tools."""
        return self.__attrs


class CompilerFlags:
    """Storing flags of compilers."""

    def __init__(self) -> None:
        self.__attrs: dict[CompilerFlagsAttrs, str] = {}  # attr -> compiler_flags

    def get(self, attr: CompilerFlagsAttrs) -> str | None:
        """Getter of compiler flags."""
        return self.__attrs.get(attr)

    def set(self, attr: CompilerFlagsAttrs, new_value: str) -> None:
        """Setter of compiler flags."""
        self.__attrs[attr] = new_value

    @property
    def data(self) -> dict[CompilerFlagsAttrs, str]:
        """Return dictionary with all tools."""
        return self.__attrs


# pylint: disable=too-few-public-methods
class IUI(ABC):
    """Interface for User Interface (UI) classes."""

    @abstractmethod
    def step(self) -> None:
        """Advance the progress counter by one step."""

    @abstractmethod
    def send_message(self, sender: str, message: str) -> None:
        """Send message to user.

        :param str sender: Identifier name of sender module
        :param str message: Message to user
        """

    @abstractmethod
    def send_warning(self, sender: str, warning: str) -> None:
        """Send warning to user.

        :param str sender: Identifier name of sender module
        :param str warning: Warning to user
        """

    @abstractmethod
    def send_error(self, sender: str, error: str) -> None:
        """Send error message to user.

        :param str sender: Identifier name of sender module
        :param str error: Error message to user
        """

    @abstractmethod
    def update_message(self, build_id: str, message: str) -> None:
        """Update message for specific build.

        :param str build_id: Build identifier
        :param str message: Message to store
        """

    @abstractmethod
    def mark_success(self, message: str = "", build_id: str = "") -> None:
        """Mark build as successful.

        :param str message: Optional message
        :param str build_id: Build identifier
        """

    @abstractmethod
    def mark_failed(self, error_message: str = "", build_id: str = "") -> None:
        """Mark build as failed.

        :param str error_message: Optional error message
        :param str build_id: Build identifier
        """


class _nullUI(IUI):
    """A UI implementation that does nothing (used to suppress output)."""

    def step(self) -> None:
        pass

    def send_message(self, sender: str, message: str) -> None:
        pass

    def send_warning(self, sender: str, warning: str) -> None:
        pass

    def send_error(self, sender: str, error: str) -> None:
        pass

    def update_message(self, build_id: str, message: str) -> None:
        pass

    def mark_success(self, message: str = "", build_id: str = "") -> None:
        pass

    def mark_failed(self, error_message: str = "", build_id: str = "") -> None:
        pass


NULL_UI = _nullUI()


# pylint: disable=too-few-public-methods
class ILowLevelBuildSystem(ABC):
    """Interface for classes implementing interaction with runner (low-level build-system)."""

    @abstractmethod
    def __init__(self, project: "Project", ui: IUI):
        pass

    @abstractmethod
    def run_building(self, build: "Build") -> tuple[int, str, str]:
        """Run building via build system."""


# pylint: disable=too-few-public-methods
class IHighLevelBuildSystem(ABC):
    """Interface for classes implementing interaction with a build system.

    Represents a high-level build system abstraction.
    """

    @abstractmethod
    def __init__(
        self,
        project: "Project",
        runner: ILowLevelBuildSystem,
        ui: IUI,
    ):
        pass

    @abstractmethod
    def build(self, build: "Build") -> tuple[int, str, str]:
        """Build via build system."""


class _dummyRunner(ILowLevelBuildSystem):
    """Runner that does nothing."""

    def __init__(self):
        pass

    def run_building(self, build: "Build") -> tuple[int, str, str]:
        return (0, "", "")


DUMMY_RUNNER = _dummyRunner()


# pylint: disable=too-few-public-methods
class _dummyBuildSystem(IHighLevelBuildSystem):
    """Build system that does nothing."""

    def __init__(self):
        pass

    def build(self, build: "Build") -> tuple[int, str, str]:
        """Build via build system."""
        return (0, "", "")


DUMMY_BUILD_SYSTEM = _dummyBuildSystem()


# pylint: disable=too-few-public-methods
class BuildSystem:
    """Common class for build systems."""

    _MAX_DEPTH = 3

    def __init__(
        self,
        project: "Project",
        runner: ILowLevelBuildSystem = DUMMY_RUNNER,
        ui: IUI = NULL_UI,
    ):
        self._project = project
        self._ui = ui
        self.runner = runner

    def find_relative_path(self, file_name: str) -> str:
        """Find first directory that contains 'file_name' relative to project root.

        :param str file_name: Name of file to search relative to project root.
        :rtype: str
        :return: Path to directory that contains file relative to project root.
        """
        q_dirs: queue.Queue[tuple[str, int]] = queue.Queue()
        q_dirs.put((self._project.path, 0))
        while not q_dirs.empty():
            curr_dir = q_dirs.get()
            if curr_dir[1] >= self._MAX_DEPTH:
                continue
            if os.path.exists(os.path.join(curr_dir[0], file_name)):
                return curr_dir[0][
                    len(self._project.path) + 1 :
                ]  # /path/to/sources/[path/to/file] <- this returns
            for el in os.scandir(curr_dir[0]):
                if el.is_dir():
                    q_dirs.put((el.path, curr_dir[1] + 1))
        raise FileNotFoundError(f"Can't find {file_name}")


@dataclass
class Build:
    """Class with information about one build of project.

    :var MachineInfo build_machine: Information about the machine to build at
    :var MachineInfo run_machine: Information about the machine to profile at
    :var str build_name: Unique name of the build
    :var Toolchain | None toolchain: Toolchain used to building
    :var str | None sysroot: Path to sysroot or name of sysroot used to building
    :var list[str] executables: List of relative to `build path` paths to executables
    :var str compiler_flags: Compiler flags for the build
    :var None | int jobs: Number of building jobs
    :var bool successfully_built: Flag of completness of build
    """

    build_machine: MachineInfo
    run_machine: MachineInfo
    build_name: str
    executables: list[str]
    toolchain: Toolchain | None
    sysroot: str | None
    compiler_flags: CompilerFlags | None
    config_flags: None | str
    jobs: None | int = None
    successfully_built: bool = True


@dataclass
class Project:
    """Class with information about project and his builds.

    :var str path: Path to project for research.
    :var list[Build] builds: List of project configurations to be build.
    :var IHighLevelBuildSystem build_system: High-level build system.
    """

    builds: list[Build]

    def __init__(
        self,
        path: str,
        builds: list[Build] | None = None,
        build_system: IHighLevelBuildSystem = DUMMY_BUILD_SYSTEM,
    ):
        self.path: str = path
        if builds is None:  # what's wrong with python?? (pylint W0102)
            self.builds = []
        else:
            self.builds = builds
        if not isinstance(self.builds, list):
            raise TypeError("class Project: 'builds' must have a list type")
        self.build_system = build_system
