"""Opencode subcommands."""

import subprocess
from argparse import ArgumentParser, Namespace

from amphimixis.amixis.commands.opencode.install import run_opencode_install
from amphimixis.amixis.commands.opencode.run import run_opencode_run
from amphimixis.amixis.commands.opencode.uninstall import run_opencode_uninstall

HELP_MESSAGE = "Run Amphimixis LLM-agent in Opencode"

_INSTALL_SUBCMD = "install"
_UNINSTALL_SUBCMD = "uninstall"
_RUN_SUBCMD = "run"


def add_args(parser: ArgumentParser) -> None:
    """Add arguments for Opencode command.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    subparsers = parser.add_subparsers(
        dest="opencode_subcommand", title="Opencode options"
    )
    subparsers.required = False

    install_parser = subparsers.add_parser(
        _INSTALL_SUBCMD,
        help="install Amphimixis LLM-agent with tools into Opencode locally or globally",
    )
    install_parser.add_argument(
        "-g",
        "--global",
        action="store_true",
        dest="is_global",
        help="install globally into $XDG_CONFIG_HOME/opencode",
    )

    uninstall_parser = subparsers.add_parser(
        _UNINSTALL_SUBCMD,
        help="remove Amphimixis LLM-agent with tools from Opencode locally or globally",
    )
    uninstall_parser.add_argument(
        "-g",
        "--global",
        action="store_true",
        dest="is_global",
        help="uninstall globally from $XDG_CONFIG_HOME/opencode",
    )

    run_parser = subparsers.add_parser(
        _RUN_SUBCMD,
        help="run Amphimixis LLM-agent with a specialized prompt (package mode)",
    )
    run_parser.add_argument(
        "prompt",
        type=str,
        help="prompt to pass to Opencode",
    )
    run_parser.add_argument(
        "--no-processing-output",
        action="store_true",
        help="disable processing of Opencode output and print it raw",
    )


def run_opencode(args: Namespace, extra_args: list[str]) -> bool:
    """Execute opencode subcommand.

    :param Namespace args: parsed command line arguments
    :param list[str] extra_args: additional arguments passed to the subcommand
    :return: True if command succeeded, False otherwise
    :rtype: bool
    """
    opencode_subcommand = args.opencode_subcommand

    if opencode_subcommand == _INSTALL_SUBCMD:
        return run_opencode_install(is_global=args.is_global)
    if opencode_subcommand == _UNINSTALL_SUBCMD:
        return run_opencode_uninstall(is_global=args.is_global)
    if opencode_subcommand == _RUN_SUBCMD:
        return run_opencode_run(
            prompt=args.prompt,
            no_processing_output=args.no_processing_output,
            extra_args=extra_args,
        )

    return subprocess.run(["opencode"] + extra_args, check=False).returncode == 0
