"""Shared helpers for doxis subcommands."""

import os
import signal
import subprocess
import time
from argparse import Namespace
from contextlib import suppress
from pathlib import Path

DEFAULT_IMAGE = "amphimixis-opencode:latest"
_DOXIS_DIR_REL = Path("amphimixis-integrations/doxis")
_CLEANUP_TIMEOUT = 30
_TERMINATE_TIMEOUT = 5
_WAIT_INTERVAL = 0.2


class _ScriptLauncher:
    """Own a script process group until execution or cancellation finishes."""

    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None
        self._cancel_signal: int | None = None
        self._cancelled_at = 0.0
        self._signal_forwarded = False
        self._shutdown_stage = 0

    def run(self, command: list[str], env: dict[str, str]) -> bool:
        """Run the script with temporary signal handlers and reap it on exit."""
        previous = {
            signum: signal.getsignal(signum)
            for signum in (signal.SIGINT, signal.SIGTERM)
        }
        try:
            for signum in previous:
                signal.signal(signum, self._cancel)
            with subprocess.Popen(command, env=env, start_new_session=True) as process:
                self._process = process
                self._forward_cancellation()
                returncode = self._wait()
                if self._cancel_signal is not None:
                    print("Cancelled.")
                    return False
                return returncode == 0
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)

    def _cancel(self, signum: int, _frame) -> None:
        """Record and forward only the first cancellation signal."""
        if self._cancel_signal is not None:
            return
        self._cancel_signal = signum
        self._cancelled_at = time.monotonic()
        self._forward_cancellation()

    def _forward_cancellation(self) -> None:
        """Deliver cancellation once, including when it arrived during startup."""
        if (
            self._process is not None
            and self._cancel_signal is not None
            and not self._signal_forwarded
        ):
            self._signal_forwarded = True
            self._signal_group(self._cancel_signal)

    def _wait(self) -> int:
        """Allow cleanup to finish before escalating an unresponsive script."""
        assert self._process is not None
        while True:
            try:
                return self._process.wait(timeout=_WAIT_INTERVAL)
            except subprocess.TimeoutExpired:
                self._escalate_shutdown()

    def _escalate_shutdown(self) -> None:
        """Bound cancellation time without immediately killing the shell trap."""
        if self._cancel_signal is None:
            return
        elapsed = time.monotonic() - self._cancelled_at
        if self._shutdown_stage == 0 and elapsed >= _CLEANUP_TIMEOUT:
            print(
                "error: pipeline cleanup timed out; container removal is unconfirmed."
            )
            self._shutdown_stage = 1
            self._signal_group(signal.SIGTERM)
        elif (
            self._shutdown_stage == 1
            and elapsed >= _CLEANUP_TIMEOUT + _TERMINATE_TIMEOUT
        ):
            self._shutdown_stage = 2
            self._signal_group(signal.SIGKILL)

    def _signal_group(self, signum: int) -> None:
        """Signal this launcher's group, tolerating a concurrent child exit."""
        assert self._process is not None
        with suppress(ProcessLookupError):
            os.killpg(self._process.pid, signum)


def _resolve_doxis_script(name: str) -> Path | None:
    """Locate a doxis helper script from the repo checkout.

    :param str name: script file name (e.g. ``process-projects.sh``)
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
        return _ScriptLauncher().run(["bash", str(script), *script_args], env)
    except FileNotFoundError as exc:
        print(f"error: failed to launch pipeline: {exc}")
        return False
