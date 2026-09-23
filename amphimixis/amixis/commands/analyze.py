"""Analyze command."""

from argparse import ArgumentParser
from os import path

import yaml

from amphimixis.amixis.utils import add_path_arg
from amphimixis.core.analyzer import analyze
from amphimixis.core.binary_analyzer import analyze_vectorization
from amphimixis.core.general import IUI, NULL_UI, Arch, Project

HELP_MESSAGE = "Analyze the project and detect existing CI, tests, build systems, etc."

VECTOR_ARCH_MAP = {
    "x86": Arch.X86,
    "riscv": Arch.RISCV,
    "arm": Arch.ARM,
}


def add_args(parser: ArgumentParser) -> None:
    """Add arguments for analyze command.

    :param ArgumentParser parser: subcommand parser to which arguments are added
    """
    add_path_arg(parser)
    parser.add_argument(
        "--vector",
        "-v",
        action="store",
        dest="vector",
        choices=list(VECTOR_ARCH_MAP),
        metavar="ARCH",
        help=(
            "Analyze binary for vector instructions. "
            "Path positional arg becomes the binary path. "
            "Arch: x86, riscv, arm (e.g. -v rvv)"
        ),
    )


def run_analyze(project: Project, ui: IUI = NULL_UI) -> bool:
    """Execute project analysis.

    :param Project project: Project instance to analyze
    :param IUI ui: User interface for progress display
    :return: True if analysis succeeded, False otherwise
    :rtype: bool
    """
    project_name = path.basename(path.normpath(project.path))
    ui.update_message(project_name, "Analyzing project...")

    if not (results := analyze(project)):
        ui.mark_failed("Analysis failed. See amphimixis.log for details.")
        return False
    sresults = yaml.safe_dump(results).replace("[]", "not found")
    ui.send_message("Analysis", sresults)
    return True


def run_vector_analyse(binary_path: str, arch_str: str) -> bool:
    """Analyze a binary for vector instructions.

    :param str binary_path: Path to the binary to analyze
    :param str arch_str: Architecture string (x86, riscv, arm)
    :return: True if analysis succeeded, False otherwise
    :rtype: bool
    """
    arch = VECTOR_ARCH_MAP.get(arch_str)
    if arch is None:
        print(f"Error: Unknown architecture '{arch_str}'. Use: x86, riscv, arm")
        return False

    try:
        unique, total, found = analyze_vectorization(binary_path, arch)
    except (FileNotFoundError, RuntimeError, ValueError) as e:
        print(f"Error: {e}")
        return False

    print("=== Vector instruction analysis ===")
    print(f"  Binary: {binary_path}")
    print("")
    print(f"{binary_path} --- {arch.value.upper()} --- {unique} unique / {total} total")
    if found:
        for inst, count in found:
            print(f"  {inst}: {count}")
    else:
        print("  No vector instructions detected.")
    print("")
    return True
