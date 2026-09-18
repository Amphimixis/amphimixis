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

    def _list_source_paths(self, shell: Shell, source_dir: str) -> set[str]:
        """List paths present in the source directory through the shell.

        :param Shell shell: Shell connected to the build machine.
        :param str source_dir: Path to the project source directory.
        :rtype: set[str]
        :return: Set of absolute paths existing in the source directory.
        """
        error, stdout, _ = shell.run(f"find {source_dir}/ -mindepth 1")
        if error != 0:
            return set()
        return {line.strip() for line in stdout[0] if line.strip()}

    def _clean_source_paths(self, shell: Shell, paths: set[str]) -> None:
        """Remove generated paths from the source directory.

        :param Shell shell: Shell connected to the build machine.
        :param set[str] paths: Absolute paths to remove.
        """
        if not paths:
            return
        paths_list = sorted(paths)
        _logger.info("Run cleaning generated autotools files: %s", " ".join(paths_list))
        shell.run("rm -rf " + " ".join(paths_list))

    def _find_autoconf_dir(self, shell: Shell, source_dir: str) -> str | None:
        """Find the directory containing the Autoconf project file.

        :param Shell shell: Shell connected to the build machine.
        :param str source_dir: Path to the project source directory.
        :rtype: str | None
        :return: Absolute path to the Autoconf project directory or None.
        """
        error, stdout, _ = shell.run(
            f"find {source_dir} -maxdepth 2 "
            r"\( -name 'configure.ac' -o -name 'configure.in' \) -type f"
        )
        if error != 0:
            return None
        for line in stdout[0]:
            path = line.strip()
            if path:
                return os.path.dirname(path)
        return None

    def _generate_configure(self, shell: Shell, autoconf_dir: str):
        """Generate the configure script with autogen.sh or autoreconf.

        :param Shell shell: Shell connected to the build machine.
        :param str autoconf_dir: Absolute path to the Autoconf project directory.
        :rtype: tuple[int, list, list]
        :return: Tuple of error_code, stdout, stderr returned by the generation.
        """
        marker, _, _ = shell.run(f"test -f {os.path.join(autoconf_dir, 'autogen.sh')}")
        if marker == 0:
            gen_cmd = f"cd {autoconf_dir} && ./autogen.sh"
        else:
            gen_cmd = f"cd {autoconf_dir} && autoreconf --install"
        _logger.info("Run generating configure script: %s", gen_cmd)
        return shell.run(gen_cmd)

    def build(self, build: Build) -> tuple[int, str, str]:
        """Configure and build via Autoconf.

        Generates the configure script if the project has autotools files but
        no ready configure script. Generated files are removed after the build.

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
        source_dir = shell.get_source_dir()

        generated_files: set[str] | None = None

        before = self._list_source_paths(shell, source_dir)
        autoconf_dir = self._find_autoconf_dir(shell, source_dir)

        if autoconf_dir is not None:
            configure_script = os.path.join(source_dir, autoconf_dir, "configure")
            if configure_script not in before:
                gen_err, gen_stdout, gen_stderr = self._generate_configure(
                    shell, autoconf_dir
                )
                after = self._list_source_paths(shell, source_dir)
                generated_files = after - before
                if gen_err != 0:
                    self._clean_source_paths(shell, generated_files)
                    return (
                        gen_err,
                        "".join(gen_stdout[0]),
                        "".join(gen_stderr[0]),
                    )
        else:
            configure_script = os.path.join(
                shell.get_source_dir(),
                self.find_relative_path("configure"),
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

        try:
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
        finally:
            if generated_files is not None:
                self._clean_source_paths(shell, generated_files)
