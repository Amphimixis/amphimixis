"""Opencode uninstall subcommand."""

import shutil
import subprocess
from pathlib import Path

from amphimixis.amixis.commands.opencode._utils import (
    get_opencode_config_dir_path,
    is_package_declared,
    load_package,
    save_package,
)

INSPECTOR_GENERAL_NAME = "inspector_general"

INSTALLED_MANIFEST: list[tuple[str, str | None]] = [
    ("agents", "*.md"),
    ("tools", "*.ts"),
    ("commands", "*.md"),
    ("plugins", "*.ts"),
    ("node_modules/inspector_general.ts", None),
]


def run_opencode_uninstall(is_global: bool = False) -> bool:
    """Remove Amphimixis-AI agents and tools from Opencode config directory.

    Deletes files that were placed by install and removes the declared
    ``inspector_general`` dependency from package.json and bun.lock
    (via ``bun remove``). Leaves other dependencies, ``opencode.json(c)``
    and any user-owned files untouched.

    :param bool is_global: If True uninstall from XDG_CONFIG_HOME/opencode,
        otherwise from local .opencode in current directory
    :return: True if command completed, False otherwise
    :rtype: bool
    """
    src_root = _get_source_root()
    config_dir = get_opencode_config_dir_path(is_global=is_global)

    print(f"Uninstalling from {config_dir}")

    removed = 0
    skipped = 0

    for location, pattern in INSTALLED_MANIFEST:
        if pattern is None:
            dst = config_dir / location
            if dst.is_file():
                dst.unlink()
                removed += 1
                print(f"  Removed {location}")
            else:
                skipped += 1
            continue

        src_dir = src_root / location
        if not src_dir.exists():
            continue
        for src_file in src_dir.glob(pattern):
            dst = config_dir / location / src_file.name
            if dst.is_file():
                dst.unlink()
                removed += 1
                print(f"  Removed {location}/{src_file.name}")
            else:
                skipped += 1

    package_json = config_dir / "package.json"
    if is_package_declared(package_json, INSPECTOR_GENERAL_NAME):
        if shutil.which("bun") is not None:
            subprocess.run(
                ["bun", "remove", INSPECTOR_GENERAL_NAME],
                cwd=config_dir,
                check=False,
            )
        _remove_declared_dependency(package_json, INSPECTOR_GENERAL_NAME)
        _remove_installed_package(config_dir / "node_modules" / INSPECTOR_GENERAL_NAME)
        print(f"  Removed {INSPECTOR_GENERAL_NAME} package")
        removed += 1

    print()
    print("Uninstall complete!")
    print(f"  Removed: {removed}")
    if skipped:
        print(f"  Not installed (skipped): {skipped}")

    return True


def _remove_declared_dependency(package_json: Path, name: str) -> None:
    """Remove the dependency entry from the config package.json."""
    package = load_package(package_json)
    dependencies = package.get("dependencies")
    if dependencies and name in dependencies:
        del dependencies[name]
        save_package(package_json, package)


def _remove_installed_package(path: Path) -> None:
    """Remove an installed package from the config node_modules.

    The entry may be a file, a directory or a symlink.
    """
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _get_source_root() -> Path:
    """Return the root of the opencode source tree.

    Uses __file__ to locate the amphimixis-integrations/opencode directory.
    """
    self_path = Path(__file__).resolve()
    # {repo_path}/amphimixis/amixis/commands/opencode/uninstall.py
    project_root = self_path.parent.parent.parent.parent.parent.resolve()
    return project_root / "amphimixis-integrations" / "opencode"
