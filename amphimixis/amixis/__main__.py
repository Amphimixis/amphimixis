#!/usr/bin/env python3

"""Amphimixis CLI tool for build automation and profiling."""

import shutil
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
def _main() -> bool:
    """There is an entry point the Amphimixis console utility.

    :return: True if command succeeded, False otherwise
    :rtype: bool
    """
    parser = create_parser()
    args, extra_args = parser.parse_known_args()

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
    if hasattr(args, "path"):
        if not args.path:
            parser.print_help()
            return False
        project = general.Project(str(Path(args.path).expanduser().resolve()))

    config_file = DEFAULT_CONFIG_PATH
    if args.command in ("run", "build", "profile"):
        if args.config is None:
            if not DEFAULT_CONFIG_PATH.exists():
                script_dir = Path(__file__).parent.resolve()
                shutil.copy(
                    script_dir / ".." / "samples" / "local.yml",
                    Path("input.yml").resolve(),
                )
                print("Created input.yml from samples/local.yml")
        else:
            config_file = Path(args.config).expanduser().resolve()  # type: ignore[arg-type]

    target_events = args.events if hasattr(args, "events") else None
    match args.command:
        case "init":
            return cmd.run_init(args.sample_name)
        case "run":
            return cmd.run_full_pipeline(
                project,
                config_file,
                ui,
                events=target_events,
                stats_format=args.stats_format,
            )
        case "analyze":
            if args.vector:
                return cmd.run_vector_analyse(args.path, args.vector)
            return cmd.run_analyze(project, ui)
        case "build":
            return cmd.run_build(project, config_file, ui, build_name=args.build_name)
        case "profile":
            return cmd.run_profile(
                project,
                config_file,
                ui,
                events=target_events,
                build_name=args.build_name,
                stats_format=args.stats_format,
            )
        case "compare":
            return cmd.run_compare(
                args.file1,
                args.file2,
                target_events,
                args.max_rows,
                ui,
                cross_table_format=args.cross_table_format,
            )
        case "validate":
            return cmd.validate_cmd(args, ui)
        case "clean":
            return cmd.run_clean(args)
        case "add":
            return cmd.run_add(args)
        case "opencode":
            return cmd.run_opencode(args, extra_args)
        case _:
            parser.print_help()
            return False


if __name__ == "__main__":
    sys.exit(0 if _main() else 1)


def main() -> bool:
    """Reverse return value."""
    return not _main()
