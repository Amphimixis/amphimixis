"""Shared helpers for doxis subcommands."""

import os
import subprocess
from argparse import Namespace
from pathlib import Path

DEFAULT_IMAGE = "amphimixis-opencode:latest"
_DOXIS_DIR_REL = Path("amphimixis-integrations/doxis")


def _resolve_doxis_script(name: str) -> Path | None:
    """Locate a doxis helper script from the repo checkout.

    :param str name: script file name (e.g. ``run.sh``)
    :return: script path if found, None otherwise
    :rtype: Path | None
    """
    for start in (Path(__file__).resolve().parent, Path.cwd()):
        for parent in (start, *start.parents):
            candidate = parent / _DOXIS_DIR_REL / name
            if candidate.is_file():
                return candidate
    return None


def _image_env(args: Namespace) -> dict[str, str]:
    """Build the child process environment with the image override applied.

    :param Namespace args: parsed command line arguments
    :return: environment mapping for the child process
    :rtype: dict[str, str]
    """
    env = dict(os.environ)
    if args.image:
        env["AMPHIMIXIS_IMAGE"] = str(args.image)
    return env


def _launch(script: Path, script_args: list[str], env: dict[str, str]) -> bool:
    """Launch a doxis script.

    :param Path script: script path
    :param list[str] script_args: script arguments (without argv[0])
    :param dict[str, str] env: environment for the child process
    :return: True if the script succeeded, False otherwise
    :rtype: bool
    """
    try:
        completed = subprocess.run(
            ["bash", str(script), *script_args], env=env, check=False
        )
        return completed.returncode == 0
    except FileNotFoundError as exc:
        print(f"error: failed to launch pipeline: {exc}")
        return False
    except KeyboardInterrupt:
        print("Cancelled.")
        return False
