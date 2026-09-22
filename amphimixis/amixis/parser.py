"""Parser for Amphimixis CLI with subcommands."""

import argparse
from argparse import ArgumentParser

from amphimixis.amixis.commands import COMMANDS

MAIN_EXAMPLES = """
Examples:
  amixis init sample_name
      → Creates configuration file by sample. Available samples: local, distributed, distributed-cross, qemu.

  amixis run /path/to/project
      → Performs full project analysis, generates configuration files,
        runs the build process, and performs profiling.

  amixis run --config=config_file /path/to/project
      → Uses a custom configuration file (default: input.yml) for all steps:
        analysis, configuration, building, and profiling.

  amixis run /path/to/project --events cycles cache-misses
      → Run pipeline and profile only the 'cycles' and 'cache-misses' events.

  amixis analyze /path/to/project
      → Analyzes the project and detects existing CI, tests, benchmarks, etc.

  amixis build /path/to/project
      → Builds the project according to the generated configuration.

  amixis profile /path/to/project --events cycles
      → Profiles the project using specified perf events (e.g., cycles).

  amixis validate /path/to/input/config
      → Checks the correctness of the configuration file.

  amixis compare file1.scriptout file2.scriptout
      → Compares two perf output files (.scriptout) and displays the results.

  amixis compare file1.scriptout file2.scriptout --events cycles
      → Compares two perf output files (.scriptout) using only the 'cycles' event.

  amixis add input
      → Interactively creates an input.yml configuration file.

  amixis add toolchain
      → Interactively adds a toolchain to the global configuration.

  amixis clean
      → Interactive mode: select builds to clean.

  amixis clean build1 build2
      → Cleans specific builds by name.

  amixis clean --all
      → Cleans all build directories.
"""

EXAMPLES = {
    "init": """Examples:
  amixis init sample_name
      → Creates configuration file by sample. Available samples: \
        local, distributed, distributed-cross, qemu.""",
    "run": """Examples:
  amixis run /path/to/project
      → Run full pipeline (analyze, build, profile) on project
  amixis run --config=config_file /path/to/project
      → Run with custom config file
  amixis run /path/to/project --events cycles cache-misses
      → Run pipeline and profile only the 'cycles' and 'cache-misses' events""",
    "analyze": """Examples:
  amixis analyze /path/to/project
      → Analyze project and detect existing CI, tests, build systems, etc.""",
    "build": """Examples:
  amixis build /path/to/project
      → Build project according to generated configuration files
  amixis build /path/to/project --config custom.yml
      → Build with custom config file""",
    "profile": """Examples:
  amixis profile /path/to/project
      → Profile performance of builds
  amixis profile /path/to/project --events cycles cache-misses
      → Profile with specific perf events""",
    "validate": """Examples:
  amixis validate /path/to/input/config
      → Check config file correctness""",
    "compare": """Examples:
  amixis compare file1.scriptout file2.scriptout
      → Compare two perf output files
  amixis compare file1.scriptout file2.scriptout --max-rows 10
      → Compare with max 10 rows per event
  amixis compare file1.scriptout file2.scriptout --events cycles
      → Compare only the 'cycles' event""",
    "clean": """Examples:
  amixis clean
      → Interactive mode: select builds to clean
  amixis clean build1 build2
      → Cleans specific builds by name
  amixis clean --all
      → Cleans all build directories""",
    "add": """Examples:
  amixis add input
      → Interactively create input.yml configuration file
  amixis add toolchain
      → Interactively add a toolchain to global config""",
}


class CustomHelpFormatter(argparse.RawTextHelpFormatter):
    """Custom formatter for better alignment."""

    def __init__(self, prog):
        super().__init__(prog, max_help_position=35)


def create_parser() -> ArgumentParser:
    """Create the main argument parser with subcommands.

    :return: Configured argument parser for Amphimixis CLI
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="amixis",
        formatter_class=CustomHelpFormatter,
        add_help=False,
        usage=argparse.SUPPRESS,
    )

    parser.add_argument(
        "-h",
        "--short-help",
        action="store_true",
        dest="short_help",
        help="show short help without examples",
    )
    parser.add_argument(
        "--help",
        action="store_true",
        dest="full_help",
        help="show full help with examples",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="subcommands",
        required=False,
        metavar="<command>",
    )

    for name, cmd in COMMANDS.items():
        epilog = EXAMPLES.get(name, "")
        subparser = subparsers.add_parser(
            name,
            help=cmd.HELP_MESSAGE,
            epilog=epilog,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        cmd.add_args(subparser)

    return parser
