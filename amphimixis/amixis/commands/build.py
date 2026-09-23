"""Build command."""

from argparse import ArgumentParser

from amphimixis.amixis.utils import add_config_arg, add_path_arg
from amphimixis.core import Builder, parse_config
from amphimixis.core.general import IUI, NULL_UI, Project

HELP_MESSAGE = "Build the project according to the generated configuration files"


def add_args(parser: ArgumentParser) -> None:
    """Add arguments for build command.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    # pylint: disable=duplicate-code
    add_path_arg(parser)
    add_config_arg(parser)
    parser.add_argument(
        "--build-name",
        type=str,
        help="name of the specific build to build (from input.yml)",
    )


def run_build(
    project: Project,
    config_file_path: str,
    ui: IUI = NULL_UI,
    build_name: str | None = None,
) -> bool:
    """Execute project build.

    :param Project project: Project instance to build
    :param str config_file_path: Path to YAML configuration file
    :param IUI ui: User interface for progress display
    :param str | None build_name: Optional name of a specific build to run
    :return: True if at least one build succeeded, False otherwise
    :rtype: bool
    """
    if not project.builds and not parse_config(
        project, config_file_path=config_file_path, ui=ui
    ):
        return False

    there_are_built = False
    for build in project.builds:
        if build_name and build.build_name != build_name:
            continue
        if Builder.build_for_linux(project, build, ui):
            there_are_built = True
            ui.mark_success("Build passed!")
        else:
            ui.mark_failed(build_id=build.build_name, error_message="Building failed")

    return there_are_built
