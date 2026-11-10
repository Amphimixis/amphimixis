"""Doxis subcommands."""

from argparse import ArgumentParser, Namespace

from amphimixis.amixis.commands.doxis.build_image import _run_build_image
from amphimixis.amixis.commands.doxis.run import _run_pipeline

HELP_MESSAGE = "Run dockerized amphimixis (doxis)"
_BUILD_IMAGE_SUBCMD = "build-image"
_RUN_SUBCMD = "run"
_RUN_OPTIONS = (
    "limit",
    "skip",
    "repo",
    "config",
    "model",
    "prompt",
    "workdir",
    "resume",
    "extra_docker",
)

__all__ = ["HELP_MESSAGE", "add_args", "run_doxis"]


class _ActionParser(ArgumentParser):
    """Parse peer actions and options, including options between actions."""

    _parsing_intermixed = False

    def parse_known_args(self, args=None, namespace=None):
        """Normalize Doxis actions after parsing intermixed options."""
        if self._parsing_intermixed:
            return super().parse_known_args(args, namespace)
        self._parsing_intermixed = True
        try:
            parsed, unknown = self.parse_known_intermixed_args(args, namespace)
        finally:
            self._parsing_intermixed = False
        self._normalize_actions(parsed)
        return parsed, unknown

    def _normalize_actions(self, args: Namespace) -> None:
        """Validate action order and separate the list file from actions."""
        actions, operands = self._parse_actions(args)
        args.build_image = _BUILD_IMAGE_SUBCMD in actions
        args.run_pipeline = _RUN_SUBCMD in actions
        args.list_file = operands[0] if operands else None
        if not args.run_pipeline:
            self._validate_build_only(args)
        del args.operands

    def _parse_actions(self, args: Namespace) -> tuple[set[str], list[str]]:
        """Extract the action group and reject misplaced or repeated actions."""
        actions = {args.doxis_subcommand}
        operands = list(args.operands)
        if operands and operands[0] in (_RUN_SUBCMD, _BUILD_IMAGE_SUBCMD):
            action = operands.pop(0)
            if action in actions:
                self.error(f"duplicate action: {action}")
            actions.add(action)
        if len(operands) > 1 or any(
            operand in (_RUN_SUBCMD, _BUILD_IMAGE_SUBCMD) for operand in operands
        ):
            self.error("actions must appear once before a single list file")
        return actions, operands

    def _validate_build_only(self, args: Namespace) -> None:
        """Reject run inputs when only the image build action is selected."""
        if args.list_file is not None:
            self.error("a list file requires the run action")
        supplied = [
            name
            for name in _RUN_OPTIONS
            if getattr(args, name) is not None
            and (name != "extra_docker" or args.extra_docker)
        ]
        if supplied:
            self.error("run options require the run action: " + ", ".join(supplied))


def add_args(parser: ArgumentParser) -> None:
    """Add arguments for doxis command.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    subparsers = parser.add_subparsers(
        dest="doxis_subcommand", title="Doxis actions", parser_class=_ActionParser
    )
    subparsers.required = False

    for action, description in (
        (_RUN_SUBCMD, "run the pipeline; combine with build-image to build first"),
        (_BUILD_IMAGE_SUBCMD, "build the image; combine with run to run afterward"),
    ):
        action_parser = subparsers.add_parser(
            action,
            help=description,
            description="Select either action or both in either order before the list "
            "file. Combined actions always build before running. "
            "Options other than --image require run. A list file is required "
            "for run unless --resume is supplied.",
        )
        action_parser.set_defaults(doxis_subcommand=action)
        _add_run_args(action_parser)


def _add_run_args(parser: ArgumentParser) -> None:
    """Add shared options and positional operands for either first action."""
    parser.add_argument(
        "operands",
        nargs="*",
        metavar="ACTION_OR_LIST",
        help="optional other action (run or build-image), followed by a list file; "
        "actions may appear once in either order",
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
        default=None,
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
    workspace = parser.add_mutually_exclusive_group()
    workspace.add_argument(
        "--workdir",
        type=str,
        default=None,
        metavar="PATH",
        help="parent directory for new numbered <project>_<i> workspaces",
    )
    workspace.add_argument(
        "--resume",
        type=str,
        default=None,
        metavar="PATH",
        help="resume an existing workspace without a list file; recover project "
        "and model from pipeline.log and read it before continuing",
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
    if subcommand is None:
        _print_help()
        return True
    if args.run_pipeline:
        return _run_pipeline(args, build_image=args.build_image)
    return _run_build_image(args)
