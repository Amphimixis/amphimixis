#!/usr/bin/env python3

"""Amphimixis CLI tool for build automation and profiling."""

import sys
from pathlib import Path

from amphimixis.amixis.commands import COMMANDS
from amphimixis.amixis.console_animation_printer import ConsoleAnimationPrinter
from amphimixis.amixis.parser import MAIN_EXAMPLES, create_parser
from amphimixis.core import general
from amphimixis.core.general.constants import DEFAULT_CONFIG_PATH


def print_help(commands, full=False) -> None:
    """Print short help without examples.

    :param dict commands: Dictionary of subcommands (name -> module)
    :param bool full: Whether to show full help with examples
    """
    print(
        "amixis [-h] {run, analyze, build, profile, validate, compare, clean, add} ...\n"
    )
    print(
        "Amphimixis — an automated project intelligence and evaluation tool\n"
        "for performance and migration readiness.\n"
    )
    print("options:")
    print("  -h, --short-help  show short help without examples")
    print("  --help           show full help with examples\n")
    print("subcommands:")
    for name, cmd in commands.items():
        print(f"  {name:12} - {cmd.HELP_MESSAGE}")
    if full:
        print("\n" + MAIN_EXAMPLES)


# pylint: disable=too-many-branches
def main() -> bool:
    """Run the Amphimixis CLI tool.

    :return: True if command succeeded, False otherwise
    :rtype: bool
    """
    parser = create_parser()
    args = parser.parse_args()

    if args.short_help:
        print_help(COMMANDS, False)
        return True

    if args.full_help:
        print_help(COMMANDS, True)
        return True

    if args.command is None:
        print_help(COMMANDS, False)
        return True

    ui = ConsoleAnimationPrinter()

    cmd = COMMANDS.get(args.command)
    if cmd is None:
        parser.print_help()
        return False

    project = None
    if args.command in ("run", "analyze", "build", "profile"):
        if not args.path:
            parser.print_help()
            return False
        project = general.Project(str(Path(args.path).expanduser().resolve()))

    config_file = None
    if args.command in ("run", "build", "profile"):
        config_file = DEFAULT_CONFIG_PATH
        if args.config is not None:
            config_file = Path(args.config).expanduser().resolve()

    target_events = args.events if hasattr(args, "events") else None
    repeat = args.repeat if hasattr(args, "repeat") else 1
    match args.command:
        case "init":
            return cmd.run_init(args.sample_name)
        case "run":
            return cmd.run_full_pipeline(
                project, config_file, ui, events=target_events, repeat=repeat
            )
        case "analyze":
            return cmd.run_analyze(project, ui)
        case "build":
            return cmd.run_build(project, config_file, ui)
        case "profile":
            return cmd.run_profile(
                project, config_file, ui, events=target_events, repeat=repeat
            )
        case "compare":
            return cmd.run_compare(
                args.file1, args.file2, target_events, args.max_rows, ui
            )
        case "validate":
            return cmd.validate_cmd(args, ui)
        case "clean":
            return cmd.run_clean(args)
        case "add":
            return cmd.run_add(args)
        case _:
            parser.print_help()
            return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
