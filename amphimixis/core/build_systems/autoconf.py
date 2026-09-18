"""Module working with Autoconf build system."""

# pylint: disable=duplicate-code
import os

from amphimixis.core import logger
from amphimixis.core.general.general import (
    Build,
    BuildSystem,
    CompilerFlags,
    IHighLevelBuildSystem,
    Toolchain,
)
from amphimixis.core.shell import Shell

_logger = logger.setup_logger("AUTOCONF")


class Autoconf(BuildSystem, IHighLevelBuildSystem):
    """Implementation of working with Autoconf build system."""

    _GNU_standard_compatibility_warn_msg = (
        "Amphimixis only uses GNU standard flags for Autoconf, "
        "if the configure script / Makefile does not meet this standard, "
        "then using your toolchains and compilation flags may not work, "
        "you can fix it manually by specifying them in the config_flags "
        "field in the format used by the current configure script"
    )

    def _attrs_map(self, tool: str) -> str:
        value = tool.upper().split("_COMPILER", maxsplit=1)[0]
        match value.split("_")[0]:
            case "C":
                if "FLAGS" not in value:
                    value = value.replace("C", "CC", 1)
            case "FORTRAN":
                value = value.replace("FORTRAN", "FC", 1)
            case "ASM":
                value = value.replace("ASM", "AS", 1)
        return "".join(value.split("_"))

    def _generate_lang_flags(self, flags: CompilerFlags):
        ret_flags = []
        for flag, value in flags.data.items():
            ret_flags.append(f"{"".join(self._attrs_map(flag))}='{value}'")
        return " ".join(ret_flags)

    def _generate_toolchain_flags(self, toolchain: Toolchain):
        ret_flags = []
        for tool, value in toolchain.data.items():
            ret_flags.append(f"{self._attrs_map(tool)}='{value}'")
        return " ".join(ret_flags)

    def build(self, build: Build) -> tuple[int, str, str]:
        """Configure and build via Autoconf.

        :param Build build: Build to build
        :rtype: tuple[int, str, str]
        :return: Tuple of error_code, stdout, stderr
        """
        self._ui.send_warning(
            build.build_name,
            Autoconf._GNU_standard_compatibility_warn_msg,
        )
        _logger.warning(Autoconf._GNU_standard_compatibility_warn_msg)

        shell = Shell(self._project, build.build_machine, self._ui).connect()

        build_path = os.path.join(shell.get_project_workdir(), build.build_name)

        autoconf_dir = self.find_relative_path("configure")

        configure_script = os.path.join(
            shell.get_source_dir(),
            autoconf_dir,
            "configure",
        )

        conf_cmd = f"{configure_script} "
        if build.config_flags is not None:
            conf_cmd += f"{build.config_flags} "
        if build.compiler_flags is not None:
            conf_cmd += f"{self._generate_lang_flags(build.compiler_flags)} "
        if build.toolchain is not None:
            if build.toolchain.sysroot is not None:
                conf_cmd += f"SYSROOT='{build.toolchain.sysroot}' "
            conf_cmd += f"{self._generate_toolchain_flags(build.toolchain)} "

        err, stdout, stderr = shell.run(f"cd {build_path}")
        if err != 0:
            return (err, "".join(stdout[0]), "".join(stderr[0]))

        _logger.info("Run configuring with '%s'", conf_cmd)
        err, cfg_stdout, cfg_stderr = shell.run(conf_cmd)
        if err != 0:
            return (err, "".join(cfg_stdout[0]), "".join(cfg_stderr[0]))

        err, run_stdout, run_stderr = self.runner.run_building(build)

        return (
            err,
            "".join(cfg_stdout[0]) + run_stdout,
            "".join(cfg_stderr[0]) + run_stderr,
        )
