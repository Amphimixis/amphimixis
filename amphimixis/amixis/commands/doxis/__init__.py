"""Doxis subcommands."""

from argparse import ArgumentParser, Namespace

from amphimixis.amixis.commands.doxis.build_image import _run_build_image
from amphimixis.amixis.commands.doxis.run import _run_pipeline

HELP_MESSAGE = "Run dockerized amphimixis (doxis)"
_BUILD_IMAGE_SUBCMD = "build-image"
_RUN_SUBCMD = "run"


def add_args(parser: ArgumentParser) -> None:
    """Add arguments for doxis command.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    subparsers = parser.add_subparsers(dest="doxis_subcommand", title="Doxis options")
    subparsers.required = False

    run_parser = subparsers.add_parser(
        _RUN_SUBCMD,
        help="run the pipeline over the project list (does not build the image)",
    )
    _add_run_args(run_parser)

    build_image_parser = subparsers.add_parser(
        _BUILD_IMAGE_SUBCMD,
        help="build the doxis Docker image",
    )
    _add_build_image_args(build_image_parser)


def _add_run_args(parser: ArgumentParser) -> None:
    """Add arguments for ``amixis doxis run``.

    The first positional is either the list file or the ``build-image``
    token.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    parser.add_argument(
        "target",
        nargs="?",
        default=None,
        metavar="build-image",
        help="'build-image' to build the image before running (list file "
        "comes second)",
    )
    parser.add_argument(
        "list_file",
        nargs="?",
        default=None,
        metavar="list_file",
        help="file listing project names, one per line "
        "(required; comes second after 'build-image')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="process only the first N projects",
    )
    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        metavar="M",
        help="skip first M projects (default: 0)",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        metavar="URL",
        help="explicit project repository URL, passed to the container "
        "(overrides the agent's search)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        metavar="PATH",
        help="custom opencode config (JSON) file path",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        metavar="PROVIDER/MODEL",
        help="LLM model for opencode (default: opencode/big-pickle)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        metavar="TEXT",
        help="pipeline prompt overriding the generated one ",
    )
    parser.add_argument(
        "--extra-docker",
        action="append",
        default=[],
        dest="extra_docker",
        metavar="ARG",
        help="extra argument passed through to `docker run`",
    )
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        metavar="TAG",
        help="Docker image tag (default: amphimixis-opencode:latest)",
    )


def _add_build_image_args(parser: ArgumentParser) -> None:
    """Add arguments for ``amixis doxis build-image``.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    parser.add_argument(
        "--image",
        type=str,
        default=None,
        metavar="TAG",
        help="Docker image tag (default: amphimixis-opencode:latest)",
    )


def _print_help() -> None:
    """Print help for the doxis command."""
    helper = ArgumentParser(prog="amixis doxis")
    add_args(helper)
    helper.print_help()


def run_doxis(args: Namespace) -> bool:
    """Execute the doxis subcommand.

    With no subcommand ``amixis doxis`` prints usage.

    :param Namespace args: parsed command line arguments
    :return: True if the subcommand succeeded, False otherwise
    :rtype: bool
    """
    subcommand = getattr(args, "doxis_subcommand", None)
    if subcommand == _BUILD_IMAGE_SUBCMD:
        return _run_build_image(args)
    if subcommand != _RUN_SUBCMD:
        _print_help()
        return True
    return _run_pipeline(args)
