"""Helpers for building and parsing readable, reversible profiling filenames.

This module contains utility functions for encoding build names and executable
paths into filesystem-friendly filenames and decoding them back without losing
information.
"""

import glob
import os
import pickle
import socket
from pathlib import Path

from amphimixis.core.general.constants import PERF_STATS_EXT
from amphimixis.core.general.general import Project


def build_filename(build_name: str, executable: str) -> str:
    """Build a readable filename that can be decoded back to original values.

    :param str build_name: Name of the build configuration.
    :param str executable: Path to the executable relative to the build directory.
    :return: Filename in ``<escaped-build>..<escaped-executable>`` form.
    :rtype: str
    """
    escaped_build = escape_filename_part(build_name)
    escaped_executable = escape_filename_part(os.path.normpath(executable))
    return f"{escaped_build}..{escaped_executable}"


def parse_filename(filename: str) -> tuple[str, str]:
    """Decode a filename produced by :func:`build_filename`.

    :param str filename: Encoded profiling filename without extension.
    :return: Original build name and executable path.
    :rtype: tuple[str, str]
    :raises ValueError: If `filename` does not contain the expected separator.
    """
    separator = filename.find("..")
    if separator == -1:
        raise ValueError(f"Invalid perf record filename: {filename}")

    build_name = unescape_filename_part(filename[:separator])
    executable = unescape_filename_part(filename[separator + 2 :])
    return build_name, executable


def escape_filename_part(value: str) -> str:
    """Escape a filename part into a filesystem-friendly reversible form.

    Letters, digits, and `-` are preserved. Other supported characters are
    replaced with short escape sequences so the original string can be restored
    by :func:`unescape_filename_part`.

    :param str value: Build name or executable path fragment to encode.
    :return: Encoded string safe to use inside generated filenames.
    :rtype: str
    """
    escaped = []
    for char in value:
        match char:
            case char if char.isalnum() or char == "-":
                escaped.append(char)
            case "_":
                escaped.append("__")
            case "/":
                escaped.append("_s")
            case ".":
                escaped.append("_d")
            case _:
                escaped.append(f"_x{ord(char):02x}_")
    return "".join(escaped)


def unescape_filename_part(value: str) -> str:
    """Decode a value produced by :func:`escape_filename_part`.

    :param str value: Encoded filename fragment.
    :return: Decoded original string.
    :rtype: str
    :raises ValueError: If `value` contains an invalid escape sequence.
    """
    decoded = []
    idx = 0
    while idx < len(value):
        char = value[idx]
        if char != "_":
            decoded.append(char)
            idx += 1
            continue

        if idx + 1 >= len(value):
            raise ValueError(f"Invalid escaped filename part: {value}")

        match value[idx + 1]:
            case "_":
                decoded.append("_")
                idx += 2
            case "s":
                decoded.append("/")
                idx += 2
            case "d":
                decoded.append(".")
                idx += 2
            case "x":
                hex_end = value.find("_", idx + 2)
                if hex_end == -1:
                    raise ValueError(f"Invalid escaped filename part: {value}")
                decoded.append(chr(int(value[idx + 2 : hex_end], 16)))
                idx = hex_end + 1
            case _:
                raise ValueError(f"Invalid escaped filename part: {value}")

    return "".join(decoded)


def project_name(project: Project):
    """Return the normalized project directory name.

    :param Project project: Project whose root path is used as the name source.
    :return: Basename of the normalized project path.
    :rtype: str
    """
    return os.path.basename(os.path.normpath(project.path))


def get_cache_project() -> Project:
    """Load Project object saved to first .project file."""
    project_file = glob.glob("./*.project")[0]
    with open(project_file, "rb") as file:
        project: Project = pickle.load(file)
        return project


def load_project_stats(project: Project):
    """Load serialized profiling statistics for a project.

    The statistics file is resolved from the escaped project name and
    :data:`PERF_STATS_EXT`.

    :param Project project: Project whose profiling statistics should be loaded.
    :return: Deserialized profiling statistics object.
    """
    with open(
        escape_filename_part(project_name(project)) + PERF_STATS_EXT,
        "rb",
    ) as file:
        return pickle.load(file)


def get_unique_path(base_path: Path) -> Path:
    """Return a unique file path by adding suffix if base exists.

    :param Path base_path: Base path to check
    :return: Unique path (existing or with -N suffix)
    :rtype: Path
    """
    if not base_path.exists():
        return base_path
    counter = 1
    while True:
        new_path = base_path.with_stem(f"{base_path.stem}-{counter}")
        if not new_path.exists():
            return new_path
        counter += 1


def is_port_free(port: int, host: str = "127.0.0.1") -> bool:
    """Check whether a TCP port is free to bind on the given host.

    :param int port: Port to check.
    :param str host: Host interface to test binding on.
    :return: True if the port can be bound.
    :rtype: bool
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def find_free_port(host: str = "127.0.0.1") -> int:
    """Return a currently free ephemeral TCP port on the given host.

    :param str host: Host interface to bind on.
    :return: A free port number assigned by the OS.
    :rtype: int
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])
