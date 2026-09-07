"""CLI utilities - common functions for CLI commands."""

import subprocess
import tempfile
from argparse import ArgumentParser
from pathlib import Path

from amphimixis.core.general.constants import DEFAULT_CONFIG_PATH


def add_config_arg(parser: ArgumentParser) -> None:
    """Add --config argument to a parser.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    parser.add_argument(
        "--config",
        nargs="?",
        const=str(DEFAULT_CONFIG_PATH),
        metavar="CONFIG",
        help="use a specific config file (default: input.yml)",
    )


def add_path_arg(parser: ArgumentParser) -> None:
    """Add positional 'path' argument to a parser.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    parser.add_argument(
        "path",
        type=str,
        help="path to the project directory",
    )


def add_repeat_arg(parser: ArgumentParser) -> None:
    """Add --repeat argument to a parser.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        metavar="N",
        help="repeat profiling N times (default: 1)",
    )


def add_events_arg(parser: ArgumentParser) -> None:
    """Add --events argument to a parser.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    parser.add_argument(
        "--events",
        nargs="*",
        help="space-separated perf events (e.g., cycles cache-misses)",
    )


def create_temp_file(content: str) -> Path:
    """Create a temporary file with given content.

    :param str content: Content to write to the file
    :return: Path to the created temporary file
    :rtype: Path
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        return Path(f.name)


def launch_editor(editor: str, temp_path: Path) -> bool:
    """Launch the editor with the given file.

    :param str editor: Editor command to use
    :param Path temp_path: Path to the file to edit
    :return: True if editor launched successfully, False otherwise
    :rtype: bool
    """
    try:
        subprocess.call([editor, str(temp_path)])
        return True
    except FileNotFoundError:
        print(f"Error: Editor '{editor}' not found.")
        print("Please set the EDITOR environment variable to a valid editor.")
        return False
    except OSError as e:
        print(f"Error launching editor: {e}")
        return False


def read_file_content(temp_path: Path) -> str | None:
    """Read content from the file after editing.

    :param Path temp_path: Path to the file to read
    :return: File content as string, or None if an error occurred
    :rtype: str | None
    """
    try:
        with open(temp_path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        print(f"Error reading file: {e}")
        return None


def prompt_continue() -> bool:
    """Prompt user to continue after validation failure.

    :return: True if user wants to continue, False if user cancels
    :rtype: bool
    """
    try:
        answer = input("Press Enter to continue, or 'q' to cancel: ").strip().lower()
        if answer in ("q", "n", "no", "cancel"):
            print("Cancelled.")
            return False
        return True
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return False


def get_content_with_editor(editor: str, temp_path: Path) -> None | str:
    """Launch editor and read the edited content from a temporary file.

    :param str editor: Editor command (e.g., 'nano', 'vim')
    :param Path temp_path: Path to the temporary file to be edited
    :return: File content as string, or None if an error occurred.
    :rtype: str | None
    """
    if not launch_editor(editor, temp_path):
        return None
    content = read_file_content(temp_path)
    return content
