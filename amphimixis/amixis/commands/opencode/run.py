"""Opencode run subcommand."""

import shlex
import shutil
import subprocess

from amphimixis.amixis.commands.opencode.install import (
    get_opencode_config_dir_path,
)

JQ_FILTER = 'select(.type == "text") | .part.text'


def run_opencode_run(
    prompt: str, no_processing_output: bool, extra_args: list[str]
) -> bool:
    """Run Opencode non-interactively and print only its text messages.

    Uses `opencode run --format json` piped through `jq` to extract only
    messages of `text` type from the session output.

    :param str prompt: prompt to pass to Opencode
    :param bool no_processing_output: whether to disable processing of Opencode output
    :param list[str] extra_args: additional arguments to pass to Opencode
    :return: True if command succeeded, False otherwise
    """
    try:
        command = (
            "opencode run --agent amphimixis "
            + " ".join(extra_args)
            + " -- "
            + shlex.quote(prompt)
        )

        if not no_processing_output:
            jq_path = _resolve_jq()
            if jq_path is None:
                print(
                    "Install `jq` with `amixis opencode install`"
                    " or from https://jqlang.org"
                    " or run with `--no-processing-output` to see raw output"
                )
                return False
            command += " | " + jq_path + " -r " + shlex.quote(JQ_FILTER)

        subprocess.run(command, shell=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error running Opencode: {e}")
        return False


def _resolve_jq() -> str | None:
    """Give path to a jq executable, if the one is available.

    Checks the system PATH first, then the jq binary installed into the
    Opencode config directory as part of the `node-jq` Bun package.
    """
    system_jq = shutil.which("jq")
    if system_jq is not None:
        return shlex.quote(system_jq)

    for global_path in (False, True):
        config_dir = get_opencode_config_dir_path(is_global=global_path)
        node_jq = config_dir / "node_modules" / "node-jq" / "node-jq"
        if node_jq.exists():
            return "bun run node-jq"

    return None
