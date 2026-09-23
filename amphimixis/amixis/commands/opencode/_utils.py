"""Shared helpers for Opencode config dependency management."""

import json
from os import environ
from pathlib import Path


def load_package(package_json: Path) -> dict:
    """Load a package.json as a mapping, tolerating a missing or broken file."""
    if not package_json.is_file():
        return {}
    try:
        return json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_package(package_json: Path, package: dict) -> None:
    """Write a mapping back to a package.json file."""
    package_json.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")


def get_opencode_config_dir_path(is_global: bool = False) -> Path:
    """Give path to Opencode configuration directory.

    :param bool is_global: If True then give path
        to global directory otherwise local directory.
    """
    if is_global:
        config_dir = (
            Path(environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser().resolve()
        )
        return config_dir / "opencode"

    return Path(".").resolve() / ".opencode"


def is_package_declared(package_json: Path, name: str) -> bool:
    """Tell whether the config package.json declares the dependency."""
    dependencies = load_package(package_json).get("dependencies") or {}
    return name in dependencies
