"""Compare command."""

from argparse import ArgumentParser
from os import path

from amphimixis.amixis.utils import add_cross_table_format_arg, add_events_arg
from amphimixis.core.general import IUI, NULL_UI, CrossTableFormat
from amphimixis.core.perf_analyzer import main as compare_perf

HELP_MESSAGE = "Compare two perf output files (.scriptout) and display the results"


def add_args(parser: ArgumentParser) -> None:
    """Add arguments for compare command.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    add_events_arg(parser)
    add_cross_table_format_arg(parser)
    parser.add_argument(
        "file1",
        type=str,
        metavar="FILE1",
        help="path to first perf output file",
    )
    parser.add_argument(
        "file2",
        type=str,
        metavar="FILE2",
        help="path to second perf output file",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=20,
        help="maximum number of rows (symbols) to display per event (default: 20)",
    )


# pylint: disable=too-many-arguments
def run_compare(
    file1: str,
    file2: str,
    target_events: list[str] | None,
    max_rows: int,
    ui: IUI = NULL_UI,
    cross_table_format: CrossTableFormat = CrossTableFormat.ORIGINAL,
) -> bool:
    """Compare two perf output files.

    Print the top `max_rows` symbols with the most significant changes for specified events.
    Markdown cross-tables are always saved to ``cross-tables/CT-<file1>-<file2>.md``
    independently of the console output format.

    :param str file1: Scriptout filepath for comparison
    :param str file2: Scriptout filepath for comparison
    :param list[str] | None target_events: Events for comparison
    :param int max_rows: Max number of rows in comparison cross-table
    :param IUI ui: User interface for progress display
    :param CrossTableFormat cross_table_format: Console output format for cross-tables
    :return: True if command succeeded, False otherwise
    :rtype: bool
    """
    if not path.isfile(file1):
        ui.mark_failed(f"File not found: {file1}")
        return False
    if not path.isfile(file2):
        ui.mark_failed(f"File not found: {file2}")
        return False

    if (
        compare_perf(
            file1,
            file2,
            target_events,
            max_rows,
            cross_table_format=cross_table_format,
        )
        != 0
    ):
        ui.mark_failed("Comparison failed.")
        return False
    ui.mark_success("Comparison completed!")
    return True
