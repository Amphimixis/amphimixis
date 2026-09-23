"""Profile command."""

import shutil
import tempfile
from argparse import ArgumentParser
from os import path

from amphimixis.amixis.utils import (
    add_config_arg,
    add_path_arg,
    add_stats_format_arg,
)
from amphimixis.core import Profiler, Shell, parse_config
from amphimixis.core.general import IUI, NULL_UI, Project, StatsFileFormat

HELP_MESSAGE = "Profile the performance of builds"


def add_args(parser: ArgumentParser) -> None:
    """Add arguments for profile command.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    # pylint: disable=duplicate-code
    add_path_arg(parser)
    add_config_arg(parser)
    add_stats_format_arg(parser)
    parser.add_argument(
        "--build-name",
        type=str,
        help="name of the specific build to profile (from input.yml)",
    )
    parser.add_argument(
        "--events",
        nargs="*",
        help="space-separated perf events (e.g., cycles cache-misses)",
    )


def setup_profiling_environment(project: Project, ui: IUI) -> bool:
    """Set up the profiling environment by copying the built binaries to the run machines.

    :param Project project: Project instance
    :param IUI ui: User interface for progress display
    :return: True if setup succeeded, False otherwise
    :rtype: bool
    """
    success = True
    tmpdir = tempfile.mkdtemp("_amphimixis")
    for build in project.builds:
        if build.build_machine != build.run_machine:
            ui.update_message(build.build_name, "Copying built files to run machine")
            shell_build_machine = Shell(project, build.build_machine, ui=ui)
            shell_run_machine = Shell(project, build.run_machine, ui=ui)

            build_path = path.join(
                shell_build_machine.get_project_workdir(), build.build_name
            )
            if not shell_build_machine.copy_to_host(build_path, tmpdir):
                ui.mark_failed("Can't download built files from build machine")
                success = False

            if not shell_run_machine.copy_to_remote(
                path.join(tmpdir, build.build_name),
                shell_run_machine.get_project_workdir(),
            ):
                ui.mark_failed("Can't transfer built files to run machine")
                success = False

            if not shell_run_machine.copy_to_remote(
                project.path, path.dirname(shell_run_machine.get_source_dir())
            ):
                ui.mark_failed("Can't transfer source code to run machine")
                success = False

    shutil.rmtree(tmpdir)
    return success


# pylint: disable=too-many-arguments
def run_profile(
    project: Project,
    config_file_path: str,
    ui: IUI = NULL_UI,
    events: list | None = None,
    build_name: str | None = None,
    stats_format: StatsFileFormat = StatsFileFormat.JSON,
) -> bool:
    """Execute project profiling.

    :param Project project: Project instance
    :param str config_file_path: Path to YAML configuration file
    :param IUI ui: User interface for progress display
    :param list[str] | None events: List of perf events to record
    :param str | None build_name: Optional name of a specific build to profile
    :param StatsFileFormat stats_format: Format of the additional human-readable
        perf stat file (``<project name>.json`` or ``<project name>.yaml``)
    :return: True if profiling succeeded, False otherwise
    :rtype: bool
    """
    if not project.builds and not parse_config(
        project, config_file_path=config_file_path, ui=ui
    ):
        return False

    setup_profiling_environment(project, ui)

    success = True

    for build in project.builds:
        if build_name and build.build_name != build_name:
            continue
        if not build.successfully_built:
            continue
        profiler_ = Profiler(project, build, ui)
        successful_execs = profiler_.profile_all(events=events)
        profiler_.save_stats(stats_file_format=stats_format)
        profiler_.cleanup()
        if not successful_execs or (
            build.executables and successful_execs != build.executables
        ):
            ui.mark_failed("Some executables failed to be profiled")
            success = False
        else:
            ui.mark_success("Profiling completed!")

    return success
