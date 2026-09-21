"""SSH shell handler implementation."""

import time
from ctypes import ArgumentError

import paramiko

from amphimixis.core.general import MachineInfo
from amphimixis.core.shell.shell_interface import IShellHandler

_CLEAR_OUTPUT_FLAG = "CLEAR_OUTPUT_FLAG"


class _ParamikoHandler(IShellHandler):
    def __init__(
        self,
        machine: MachineInfo,
        connect_timeout: int = 15,
    ) -> None:
        if machine.auth is None or machine.address is None:
            raise ArgumentError("Authentication data is not provided")

        self.machine = machine
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.client.connect(
                hostname=machine.address,
                port=machine.auth.port,
                username=machine.auth.username,
                password=machine.auth.password,
                timeout=connect_timeout,
                look_for_keys=(machine.auth.password is None),
                allow_agent=(machine.auth.password is None),
            )
        except (OSError, paramiko.SSHException) as e:
            raise paramiko.SSHException(f"Can't connect to ssh {machine}: {e}") from e

        if (transport := self.client.get_transport()) is not None:
            transport.set_keepalive(60)
            self.chan = transport.open_session()
        else:
            raise ConnectionError("Can't get transport")

        self.chan.invoke_shell()
        self.chan.settimeout(connect_timeout)
        self._wait_until_ready("READY")
        self.chan.send(b"stty -echo\n")
        self.chan.send(b"export PS1=''\n")
        self.chan.send(b"exec bash --norc --noprofile\n")
        self._wait_until_ready("BASH_READY")
        self.chan.settimeout(None)

    def _wait_until_ready(self, ready_flag: str = "READY", timeout: int = 30) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                self.chan.send((f"echo {ready_flag}\n").encode())
            except OSError:
                continue
            while time.monotonic() < deadline:
                try:
                    line = self.stdout_readline().strip()
                except (OSError, TimeoutError):
                    break
                if line == ready_flag:
                    return
        raise OSError(f"Remote shell on {self.machine} not ready after {timeout}s")

    def __del__(self) -> None:
        self.client.close()

    def run(self, command: str) -> None:
        try:
            self.chan.send((command.strip() + "\n").encode("UTF-8"))
        except OSError as e:
            raise OSError(f"Can't send command: {e}") from e

    def stdout_readline(self) -> str:
        line = ""
        while char := self.chan.recv(1).decode("UTF-8", "replace"):
            line += char
            if char == "\n":
                break

        return line

    def stderr_readline(self) -> str:
        line = ""
        while char := self.chan.recv_stderr(1).decode("UTF-8", "replace"):
            line += char
            if char == "\n":
                break

        return line

    def _send_marker(self):
        self.chan.send((f"echo {_CLEAR_OUTPUT_FLAG}\n").encode())

    def _read_until_marker(self):
        while (line := self.stdout_readline()) != "" and _CLEAR_OUTPUT_FLAG not in line:
            pass
