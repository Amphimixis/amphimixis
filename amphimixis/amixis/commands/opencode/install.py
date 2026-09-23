"""Opencode install subcommand."""

import shutil
import string
import subprocess
from inspect import stack
from pathlib import Path

from amphimixis.amixis.commands.opencode._utils import (
    get_opencode_config_dir_path,
    is_package_declared,
)

INSPECTOR_GENERAL_NAME = "inspector_general"
_INSPECTOR_GENERAL_PACKAGE_DIR = "amphimixis-integrations/inspector_general"
_BUN_DEPENDENCIES = [
    "yaml",
    "async-mutex",
    "unified",
    "remark-parse",
    "remark-gfm",
    "node-jq",
]


def run_opencode_install(is_global: bool = False) -> bool:
    """Install Amphimixis-AI agents and tools into Opencode config directory.

    :param bool is_global: If True install globally (XDG_CONFIG_HOME/opencode),
        otherwise locally (.opencode in current directory)
    :return: True if installation succeeded, False otherwise
    :rtype: bool
    """
    self_path = Path(__file__).parent.resolve()
    project_root = self_path.parent.parent.parent.parent.resolve()
    config_dir = get_opencode_config_dir_path(is_global=is_global)

    src_root = project_root / "amphimixis-integrations" / "opencode"

    print(f"Installing Amphimixis-AI agents and tools to {config_dir}")

    install_sources = [
        (src_root / "agents", "*.md", config_dir / "agents", "agents"),
        (src_root / "tools", "*.ts", config_dir / "tools", "tools"),
        (src_root / "commands", "*.md", config_dir / "commands", "commands"),
        (src_root / "plugins", "*.ts", config_dir / "plugins", "plugins"),
    ]

    for src_dir, pattern, dst_dir, label in install_sources:
        if not src_dir.exists():
            continue
        dst_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for f in src_dir.glob(pattern):
            shutil.copy2(f, dst_dir)
            count += 1
        if label == "tools":
            _substitute_amixis_path(dst_dir)
        print(f"  Copied {count} {label}")

    package_json = config_dir / "package.json"
    package_dir = _get_inspector_general_package(project_root)

    if package_dir is not None:
        if shutil.which("bun") is not None:
            print(f"  Installing {INSPECTOR_GENERAL_NAME} package...")
            if is_package_declared(package_json, INSPECTOR_GENERAL_NAME):
                _run_bun("remove", INSPECTOR_GENERAL_NAME, cwd=config_dir)
            if not _run_bun("add", f"file:{package_dir.resolve()}", cwd=config_dir):
                return False
            print("  Installing Bun dependencies: " + ", ".join(_BUN_DEPENDENCIES))
            if not _run_bun(
                "add", "--only-missing", *_BUN_DEPENDENCIES, cwd=config_dir
            ):
                return False
            if not _run_bun("install", cwd=config_dir):
                return False
        else:
            print(
                "    bun not found — install it from https://bun.sh; "
                "inspector_general is declared in package.json, opencode "
                "will install it on its next dependency check"
            )
            return False

    print()
    print("Installation complete!")
    print("  Agents:  ", len(list((config_dir / "agents").glob("*.md"))))
    print("  Tools:   ", len(list((config_dir / "tools").glob("*.ts"))))
    print("  Commands:", len(list((config_dir / "commands").glob("*.md"))))
    print("  Plugins: ", len(list((config_dir / "plugins").glob("*.ts"))))
    print()
    print("Amphimixis-AI agents and tools are now available in opencode.")

    return True


def _get_inspector_general_package(project_root: Path) -> Path | None:
    package_dir = project_root / _INSPECTOR_GENERAL_PACKAGE_DIR
    if not (
        (package_dir / "package.json").is_file()
        and (package_dir / "inspector_general.ts").is_file()
    ):
        return None
    return package_dir


def _run_bun(*args: str, cwd: Path) -> bool:
    result = subprocess.run(["bun", *args], cwd=cwd, check=False)
    return result.returncode == 0


def _get_amixis_path() -> str:
    amixis_executable_path = [
        Path(el.filename)
        for el in stack()
        if "amixis" in el.filename or "__main__" in el.filename
    ][-1].resolve()

    if "__main__" in str(amixis_executable_path):
        src_dir = (
            amixis_executable_path.parent.parent.parent
        )  # {repo_path}/amphimixis/amixis/__main__.py
        return f"uv --project {src_dir} run python {str(amixis_executable_path)}"
    return str(amixis_executable_path)


def _substitute_amixis_path(tools_dir: Path) -> None:
    """Substitute the amixis executable path into copied tool files.

    Tools contain the `$AMIXIS_PATH` template placeholder in the `amixis`
    variable. At install time it is replaced with the resolved executable
    path so installed tools invoke the right binary.

    :param Path tools_dir: directory with freshly installed tool files
    """
    amixis_executable_path = _get_amixis_path()
    for tool_file in tools_dir.glob("*.ts"):
        content = tool_file.read_text(encoding="utf-8")
        if "$AMIXIS_PATH" not in content:
            continue
        content = string.Template(content).safe_substitute(
            AMIXIS_PATH=amixis_executable_path
        )
        tool_file.write_text(content, encoding="utf-8")
