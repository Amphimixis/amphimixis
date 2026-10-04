"""Doxis build-image subcommand."""

from argparse import Namespace

from amphimixis.amixis.commands.doxis._utils import (
    _image_env,
    _launch,
    _resolve_doxis_script,
)

_REBUILD_SCRIPT_NAME = "rebuild-and-run.sh"


def _run_build_image(args: Namespace) -> bool:
    """Build the doxis Docker image.

    :param Namespace args: parsed command line arguments
    :return: True if the build succeeded, False otherwise
    :rtype: bool
    """
    script = _resolve_doxis_script(_REBUILD_SCRIPT_NAME)
    if script is None:
        print(f"error: missing doxis script {_REBUILD_SCRIPT_NAME}")
        return False
    return _launch(script, ["--no-run"], _image_env(args))
