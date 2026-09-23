"""Run command - full pipeline."""

from argparse import ArgumentParser

from amphimixis.amixis.commands.analyze import run_analyze
from amphimixis.amixis.commands.build import run_build
from amphimixis.amixis.commands.profile import run_profile
from amphimixis.amixis.utils import (
    add_config_arg,
    add_events_arg,
    add_path_arg,
    add_stats_format_arg,
)
from amphimixis.core.general import (
    IUI,
    Project,
    ProjectStats,
    StatsFileFormat,
    constants,
    tools,
)

HELP_MESSAGE = "Run full pipeline: analyze, build and profile a project"


def add_args(parser: ArgumentParser) -> None:
    """Add arguments for run command.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    add_path_arg(parser)
    add_config_arg(parser)
    add_events_arg(parser)
    add_stats_format_arg(parser)


def show_profiling_result(project: Project) -> None:
    """Show hint or warning after profiling, based on .scriptout files in current directory.

    :param Project project: Project instance with profiling results
    """
    obj: ProjectStats = tools.load_project_stats(project)

    if not obj or not any(
        obj[build][exe].executable_run_success for build in obj for exe in obj[build]
    ):
        print("\n[!] No profiling data (.scriptout files) were generated.")
        print("\tPlease check amphimixis.log for details.")
        return

    if len(obj.keys()) == 1:
        print("\n[i] Only one profiling result was generated.")
        print("\tTo compare two results, run profiling again with a different build.")
        print("\tOnce you have two .scriptout files, compare them with:")
        print("\tamixis compare <file1.scriptout> <file2.scriptout>")
        return

    def _find_matching_exe() -> tuple[str, str, str]:
        found_build1 = None
        found_build2 = None
        found_executable = None
        build_keys = list(obj.keys())
        for build1_index in range(len(build_keys) - 1):
            for build2_key in build_keys[build1_index + 1 :]:
                build1 = obj[build_keys[build1_index]]
                build2 = obj[build2_key]

                exe_keys = set(obj[build_keys[build1_index]]) | set(obj[build2_key])

                for exe in exe_keys:
                    if exe not in build1 or exe not in build2:
                        continue
                    if (
                        build1[exe].executable_run_success
                        and build2[exe].executable_run_success
                    ):
                        found_build1 = build_keys[build1_index]
                        found_build2 = build2_key
                        found_executable = exe
                        return found_build1, found_build2, found_executable
        return "", "", ""

    build1, build2, exe = _find_matching_exe()
    if not all([build1, build2, exe]):
        print(
            "\tThere is no profiling results for the same executable in different build"
        )
        print("\tMaybe you should check profiling errors")
        return

    file1 = tools.build_filename(build1, exe) + constants.PERF_SCRIPT_EXT
    file2 = tools.build_filename(build2, exe) + constants.PERF_SCRIPT_EXT

    print("\n[>] To compare two profiling results, use:")
    print(f"\tamixis compare {file1} {file2}")


def run_full_pipeline(
    project: Project,
    config_file,
    ui: IUI,
    events: list | None = None,
    stats_format: StatsFileFormat = StatsFileFormat.JSON,
) -> bool:
    """Execute full pipeline: analyze, build, and profile a project.

    :param Project project: Project instance
    :param str | Path config_file: Path to configuration file
    :param IUI ui: User interface for progress display
    :param list[str] | None events: List of perf events to record
    :param StatsFileFormat stats_format: Format of the additional human-readable
        perf stat file (``<project name>.json`` or ``<project name>.yaml``)
    :return: True if pipeline succeeded, False otherwise
    :rtype: bool
    """
    if not run_analyze(project, ui):
        return False

    if not run_build(project, str(config_file), ui):
        return False

    if not run_profile(
        project, str(config_file), ui, events=events, stats_format=stats_format
    ):
        return False

    show_profiling_result(project)
    return True
