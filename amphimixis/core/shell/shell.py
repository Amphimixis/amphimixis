"""Module for shell operations."""

import os
import socket
import subprocess
import threading
from ctypes import ArgumentError
from typing import Self

from amphimixis.core import logger
from amphimixis.core.general import IUI, NULL_UI, MachineInfo, Project, constants
from amphimixis.core.shell.local_shell_handler import _LocalShellHandler
from amphimixis.core.shell.paramiko_shell_handler import _ParamikoHandler
from amphimixis.core.shell.shell_interface import IShellHandler

_READING_BARRIER_FLAG = "READING_BARRIER_FLAG"


# pylint: disable=too-many-instance-attributes
class Shell:
    """Shell class to manage shell operations.

    `bash` is used as shell.

    :param Project project: Project object.
    :param MachineInfo machine: machine to run profiling at.
    :param int connect_timeout: connection timeout in seconds.
    """

    def __init__(
        self,
        project: Project,
        machine: MachineInfo,
        ui: IUI = NULL_UI,
        connect_timeout=10,
    ):
        self.project = project
        self.connect_timeout = connect_timeout
        self.machine = machine
        self._logger = logger.setup_logger("SHELL")
        self._shell: IShellHandler
        self._ui = ui
        self._project_workdir: str = ""
        self._homedir: str = ""
        self._is_connected: bool = False
        self._is_local: bool = False
        self._ui_lock = threading.Lock()

    def connect(self) -> Self:
        """Connect to the shell of the machine."""
        if self.machine.address is None:
            self._create_local_shell()
        else:
            self._create_remote_shell()

        self._is_connected = True
        level, _ = self.set_paranoid(-1)
        if level != -1:
            self._logger.error(
                "Can't set /proc/sys/kernel/perf_event_paranoid to -1. Set it manually"
            )

        return self

    def _create_local_shell(self) -> None:
        self._shell = _LocalShellHandler()
        self._is_local = True

    def _create_remote_shell(self) -> None:
        if self.machine.auth is None:
            self._logger.error(
                "Remote machine [%s] has no authentication info", self.machine.address
            )

            raise ArgumentError(
                f"Remote machine [{self.machine.address}] has no authentication info"
            )

        try:
            socket.getaddrinfo(self.machine.address, None)
        except socket.gaierror as exception:
            self._logger.error("%s is unknown address", self.machine.address)
            raise ArgumentError(
                f"{self.machine.address} is unknown address"
            ) from exception

        self._shell = _ParamikoHandler(self.machine, self.connect_timeout)
        self._is_local = False

    def run(self, *commands: str) -> tuple[int, list[list[str]], list[list[str]]]:
        """Run the commands through the shell.

        - Execute commands one by one until:
            non-zero return code occurs or
            OR
            all commands have been executed.

        :param str commands: commands to be executed

        :rtype: Tuple[int, List[List[str]], List[List[str]]]
        :return: A tuple of three :

            - :int: error code of the last executed command
            - :List[List[str]]: List[str] is lines of the stdout of an executed command.
            - :List[List[str]]: List[str] is lines of the stderr of an executed command.
        """
        stdout: list[list[str]] = []
        stderr: list[list[str]] = []
        error_code = 0
        for cmd in commands:
            if error_code:
                break

            # Close stdin since reading from stdin
            # leads to blocking if the command is waiting for input.
            cmd += " 0<&-"
            self._shell.run(cmd)

            # newline added in case of it is missing in the previous output line
            self._shell.run(f'echo "\n{_READING_BARRIER_FLAG}:$?"')
            self._shell.run(f'echo "\n{_READING_BARRIER_FLAG}">&2')
            cmd_stdout: list[str] = []
            cmd_stderr: list[str] = []
            command_error_code: list[int] = []

            stdout_reader = threading.Thread(
                target=self._read_stdout_until_barrier,
                args=(cmd_stdout, command_error_code),
            )
            stderr_reader = threading.Thread(
                target=self._read_stderr_until_barrier, args=(cmd_stderr,)
            )

            stdout_reader.start()
            stderr_reader.start()
            stdout_reader.join()
            stderr_reader.join()

            error_code = command_error_code[0]
            stdout.append(cmd_stdout)
            stderr.append(cmd_stderr)

        return (error_code, stdout, stderr)

    def _read_stdout_until_barrier(
        self, output: list[str], error_code: list[int]
    ) -> None:
        while line := self._shell.stdout_readline():
            self._ui.step()

            barrier_error = self._parse_stdout_barrier(line)
            if barrier_error is not None:
                error_code.append(barrier_error)
                self._strip_barrier_separator(output)
                return

            output.append(line)

    def _read_stderr_until_barrier(self, output: list[str]) -> None:
        while line := self._shell.stderr_readline():
            self._ui.step()

            if self._is_stderr_barrier(line):
                self._strip_barrier_separator(output)
                return

            output.append(line)

    def copy_to_remote(self, source: str, destination: str) -> bool:
        """Send a file or folder to the target machine.

        Absolute paths are needed.

        :param str source: absolute path to a file or folder on the host machine
        :param str destination: absolute path to copy a file or folder to on the controlled machine

        :return: True if successfully copied else False
        """
        if self.machine.auth is None:
            _destination = destination
        else:
            _destination = (
                f"{self.machine.auth.username}@{self.machine.address}:{destination}"
            )

        return self._copy(source, _destination)

    def copy_to_host(self, source: str, destination: str) -> bool:
        """Get a file or folder from the target machine.

        Absolute paths are needed.

        :param str source: absolute path to a file or folder on the controlled machine
        :param str destination: absolute path to copy a file or folder to on the host machine

        :return: True if successfully copied else False
        """
        if self.machine.auth is None:
            _source = source
        else:
            _source = f"{self.machine.auth.username}@{self.machine.address}:{source}"

        return self._copy(_source, destination)

    def get_project_workdir(self) -> str:
        """Get a working directory for amphimixis.

        :rtype: str
        :return: In case of remote machine:
                 expanded `~/${AMPHIMIXIS_DIRECTORY_NAME}/${PROJECT_NAME}_builds`.

                 In case of local machine: python process current working directory.
        """
        if self._project_workdir != "":
            return self._project_workdir

        if not self._is_connected:
            self.connect()

        if self._is_local:
            self._project_workdir = os.getcwd()
            return self._project_workdir

        self._project_workdir = os.path.join(
            self.get_home(),
            constants.AMPHIMIXIS_DIRECTORY_NAME,
            os.path.basename(os.path.normpath(self.project.path)) + "_builds",
        )

        return self._project_workdir

    def get_home(self) -> str:
        """Get a home directory for current connection (user@machine).

        :rtype: str
        :return: Expanded `~` for the current connection (user@machine).
        """
        if self._homedir != "":
            return self._homedir

        if not self._is_connected:
            self.connect()

        if self._is_local:
            self._homedir = os.path.expanduser("~")
            if self._homedir == "":
                self._logger.error("Can't get homedir for [local] machine")
                raise RuntimeError("Can't get homedir for [local] machine")
            return self._homedir

        error, stdout, _ = self.run("echo ~")

        if self.machine.auth is None:
            self._logger.error(
                "Remote machine [%s] has no authentication info", self.machine.address
            )

            raise ArgumentError(
                f"Remote machine [{self.machine.address}] has no authentication info"
            )

        if error != 0:
            self._logger.error(
                "Can't get homedir for [%s@%s] ",
                self.machine.auth.username,
                self.machine.address,
            )

            raise RuntimeError(
                f"Can't get homedir for [{self.machine.auth.username}@{self.machine.address}]"
            )

        self._homedir = stdout[0][0].strip()
        return self._homedir

    def get_source_dir(self) -> str:
        """Get a directory for the project source code on the target machine.

        :rtype: str
        :return: In case of remote machine: expanded
            `~/${AMPHIMIXIS_DIRECTORY_NAME}/${PROJECT_NAME}`.
            In case of local machine: project path.
        """
        if self._is_local:
            return self.project.path

        return os.path.join(
            self.get_home(),
            constants.AMPHIMIXIS_DIRECTORY_NAME,
            os.path.basename(self.project.path),
        )

    def set_paranoid(self, level: int) -> tuple[int, bool]:
        """Set perf_event_paranoid to the given level.

        :param int level: The level to set perf_event_paranoid to.
            Should be an integer between -1 and 3.

        :rtype: tuple[int, bool]
        :return: A tuple of two elements:

            - int: The current level of perf_event_paranoid.
            - bool: True if the level was set successfully, False otherwise.
        """
        if not self._is_connected:
            self.connect()

        error, _, stderr = self.run(
            f"echo '{level}' > /proc/sys/kernel/perf_event_paranoid"
        )

        if error != 0:
            self._logger.error("Can't set perf_event_paranoid: %s", "".join(stderr[0]))

        error, stdout, stderr = self.run("cat /proc/sys/kernel/perf_event_paranoid")

        set_code = 0
        if error != 0:
            self._logger.error("Can't read perf_event_paranoid: %s", "".join(stderr[0]))
            return (0, False)

        set_code = int(stdout[0][0])

        return (set_code, set_code == level)

    def _copy(self, source: str, destination: str) -> bool:
        if self.machine.auth is None:
            return self._copy_local(source, destination)

        port = self.machine.auth.port
        # if None or empty string, ssh-agent is supposed
        password = self.machine.auth.password

        return self._copy_remote(source, destination, password, port)

    def _copy_remote(
        self, source: str, destination: str, password: str | None, port: int
    ) -> bool:
        self._logger.info("Copying %s -> %s", source, destination)
        sshcmd = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
        ]
        if password:
            sshcmd += [
                "-o",
                "PubkeyAuthentication=no",
                "-o",
                "PasswordAuthentication=yes",
            ]
        sshcmd += ["-p", str(port)]
        error_code = subprocess.call(
            ["sshpass"]
            + (["-p", password] if password else [])
            + [
                "rsync",
                "--checksum",
                "--archive",
                "--recursive",
                "--mkpath",
                "--copy-links",
                "--hard-links",
                "--compress",
                "--log-file=./amphimixis.log",
                "-e",
                " ".join(sshcmd),
                source,
                destination,
            ]
        )

        if error_code != 0:
            self._logger.error("Error %s -> %s", source, destination)
            return False

        self._logger.info("Success %s -> %s", source, destination)
        return True

    def _copy_local(self, source: str, destination: str) -> bool:
        self._logger.info("Copying %s -> %s", source, destination)
        error_code = subprocess.call(["cp", "-aL", source, destination])
        if error_code != 0:
            self._logger.error("Error %s -> %s", source, destination)
            return False

        self._logger.info("Success %s -> %s", source, destination)
        return True

    @staticmethod
    def _parse_stdout_barrier(line: str) -> int | None:
        stripped = line.strip()
        prefix = f"{_READING_BARRIER_FLAG}:"
        if not stripped.startswith(prefix):
            return None
        return int(stripped[len(prefix) :])

    @staticmethod
    def _is_stderr_barrier(line: str) -> bool:
        return line.strip() == _READING_BARRIER_FLAG

    @staticmethod
    def _strip_barrier_separator(lines: list[str]) -> None:
        if not lines:
            return

        if lines[-1] == "\n":
            lines.pop()
            return

        lines[-1] = lines[-1][:-1]
