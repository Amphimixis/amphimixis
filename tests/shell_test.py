# pylint: skip-file
import os
import shlex
import socket
import subprocess
import sys
import threading
from ctypes import ArgumentError

import pytest

import amphimixis.core as amphimixis
from amphimixis.core.general import constants
from amphimixis.core.shell.shell import Shell

project = amphimixis.general.Project("/tmp/amphimixis", [])  # type: ignore
READING_BARRIER_STDOUT = 'echo "\nREADING_BARRIER_FLAG:$?"'
READING_BARRIER_STDERR = 'echo "\nREADING_BARRIER_FLAG">&2'


class FakeHandler:
    def __init__(self, stdout_lines=None, stderr_lines=None):
        self.stdout_lines = list(stdout_lines or [])
        self.stderr_lines = list(stderr_lines or [])
        self.commands = []

    def run(self, command: str) -> None:
        self.commands.append(command)

    def stdout_readline(self) -> str:
        if self.stdout_lines:
            return self.stdout_lines.pop(0)
        return ""

    def stderr_readline(self) -> str:
        if self.stderr_lines:
            return self.stderr_lines.pop(0)
        return ""


@pytest.mark.unit
class TestShell:
    local_machine = amphimixis.general.MachineInfo(
        amphimixis.general.Arch.X86, None, None, None
    )
    remote_machine = amphimixis.general.MachineInfo(
        amphimixis.general.Arch.X86,
        "example.com",
        amphimixis.general.MachineAuthenticationInfo("user", "secret", 2222),
        None,
    )

    @pytest.mark.parametrize("machine", [local_machine])
    def test_copy_to_remote(
        self,
        machine: amphimixis.general.MachineInfo,
        tmp_path_factory,
    ):
        original_file = tmp_path_factory.mktemp("data0") / "original.txt"
        os.system(f"dd if=/dev/random of={original_file} bs=1 count=1234")

        shell = amphimixis.Shell(project, machine).connect()
        error, stdout, stderr = shell.run("echo $(mktemp -d)")
        assert error == 0
        remote_tmpdir = stdout[0][0].strip()
        remote_tmpfile = os.path.join(remote_tmpdir, "copy_file")

        assert shell.copy_to_remote(original_file, destination=remote_tmpfile)

        error, stdout, stderr = shell.run(f"md5sum {remote_tmpfile}")
        assert error == 0
        md5digest_remote = stdout[0][0].split()[0]

        with subprocess.Popen(
            ["md5sum", original_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as cmd:
            assert cmd.wait() == 0
            assert cmd.stdout is not None
            out = cmd.stdout.readline()
            md5digest_local = out.decode("utf-8").split()[0]

        assert md5digest_local == md5digest_remote

    def test_run_collects_stdout_and_stderr_lines(self):
        handler = FakeHandler(
            stdout_lines=["hello\n", "world\n", "\n", "READING_BARRIER_FLAG:0\n"],
            stderr_lines=["warn\n", "\n", "READING_BARRIER_FLAG\n"],
        )
        shell = Shell(project, self.local_machine)
        shell._shell = handler

        error, stdout, stderr = shell.run("echo test")

        assert error == 0
        assert stdout == [["hello\n", "world\n"]]
        assert stderr == [["warn\n"]]
        assert handler.commands == [
            "echo test 0<&-",
            READING_BARRIER_STDOUT,
            READING_BARRIER_STDERR,
        ]

    def test_run_stops_after_first_failed_command(self):
        handler = FakeHandler(
            stdout_lines=["\n", "READING_BARRIER_FLAG:7\n"],
            stderr_lines=["\n", "READING_BARRIER_FLAG\n"],
        )
        shell = Shell(project, self.local_machine)
        shell._shell = handler

        error, stdout, stderr = shell.run("false", "echo should_not_run")

        assert error == 7
        assert stdout == [[]]
        assert stderr == [[]]
        assert handler.commands == [
            "false 0<&-",
            READING_BARRIER_STDOUT,
            READING_BARRIER_STDERR,
        ]

    def test_run_drains_real_stderr_pipe_without_deadlock(self):
        shell = Shell(project, self.local_machine)
        shell._create_local_shell()

        line_length = 1024
        line_numbers = 512
        python_code = (
            "import sys; "
            f"sys.stderr.write(('x' * {line_length} + '\\n') * {line_numbers}); "
            "sys.stderr.flush(); "
            "print('done')"
        )
        command = f"{shlex.quote(sys.executable)} -c {shlex.quote(python_code)}"
        result = {}
        exception = []

        def run_command():
            try:
                result["value"] = shell.run(command)
            except Exception as error:  # pragma: no cover - re-raised below
                exception.append(error)

        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
        thread.join(timeout=10)

        try:
            if thread.is_alive():
                pytest.fail("Shell.run() deadlocked while draining stderr")

            if exception:
                raise exception[0]

            error, stdout, stderr = result["value"]

            assert error == 0
            assert stdout == [["done\n"]]
            assert len(stderr) == 1
            assert len(stderr[0]) == line_numbers
            assert all(line == ("x" * line_length) + "\n" for line in stderr[0])
        finally:
            shell._shell.__del__()

    def test_connect_uses_local_handler_for_local_machine(self, mocker):
        handler = FakeHandler()
        local_factory = mocker.patch(
            "amphimixis.core.shell.shell._LocalShellHandler", return_value=handler
        )
        paranoid = mocker.patch.object(Shell, "set_paranoid", return_value=(-1, True))

        shell = Shell(project, self.local_machine).connect()

        assert shell._shell is handler
        assert shell._is_local is True
        local_factory.assert_called_once_with()
        paranoid.assert_called_once_with(-1)

    def test_connect_raises_for_remote_machine_without_auth(self):
        machine = amphimixis.general.MachineInfo(
            amphimixis.general.Arch.X86, "example.com", None, None
        )

        with pytest.raises(ArgumentError):
            Shell(project, machine).connect()

    def test_connect_raises_for_unknown_remote_host(self, mocker):
        mocker.patch("socket.getaddrinfo", side_effect=socket.gaierror())

        with pytest.raises(ArgumentError):
            Shell(project, self.remote_machine).connect()

    def test_connect_uses_paramiko_handler_for_remote_machine(self, mocker):
        handler = FakeHandler()
        mocker.patch("socket.getaddrinfo", return_value=[object()])
        remote_factory = mocker.patch(
            "amphimixis.core.shell.shell._ParamikoHandler", return_value=handler
        )
        paranoid = mocker.patch.object(Shell, "set_paranoid", return_value=(-1, True))

        shell = Shell(project, self.remote_machine, connect_timeout=33).connect()

        assert shell._shell is handler
        assert shell._is_local is False
        remote_factory.assert_called_once_with(self.remote_machine, 33)
        paranoid.assert_called_once_with(-1)

    def test_get_project_workdir_returns_cwd_for_local_machine(self, mocker):
        shell = Shell(project, self.local_machine)
        shell._is_connected = True
        shell._is_local = True
        cwd = mocker.patch("os.getcwd", return_value="/tmp/current")

        assert shell.get_project_workdir() == "/tmp/current"
        assert shell.get_project_workdir() == "/tmp/current"
        cwd.assert_called_once_with()

    def test_get_project_workdir_builds_remote_path_and_caches_it(self, mocker):
        shell = Shell(project, self.remote_machine)
        get_home = mocker.patch.object(shell, "get_home", return_value="/home/user")
        shell._is_connected = True
        shell._is_local = False

        expected = "/home/user/amphimixis/amphimixis_builds"
        assert shell.get_project_workdir() == expected
        assert shell.get_project_workdir() == expected
        get_home.assert_called_once_with()

    def test_get_source_dir_returns_local_project_path(self):
        shell = Shell(project, self.local_machine)
        shell._is_local = True

        assert shell.get_source_dir() == project.path

    def test_get_source_dir_builds_remote_source_path(self, mocker):
        shell = Shell(project, self.remote_machine)
        mocker.patch.object(shell, "get_home", return_value="/home/user")

        assert (
            shell.get_source_dir()
            == f"/home/user/{constants.AMPHIMIXIS_DIRECTORY_NAME}/amphimixis"
        )

    def test_get_home_returns_expanduser_for_local_machine(self, mocker):
        shell = Shell(project, self.local_machine)
        shell._is_connected = True
        shell._is_local = True
        expanduser = mocker.patch("os.path.expanduser", return_value="/home/local")

        assert shell.get_home() == "/home/local"
        assert shell.get_home() == "/home/local"
        expanduser.assert_called_once_with("~")

    def test_get_home_reads_remote_home_and_caches_it(self, mocker):
        shell = Shell(project, self.remote_machine)
        shell._is_connected = True
        shell._is_local = False
        run = mocker.patch.object(
            shell, "run", return_value=(0, [["/home/remote\n"]], [[]])
        )

        assert shell.get_home() == "/home/remote"
        assert shell.get_home() == "/home/remote"
        run.assert_called_once_with("echo ~")

    def test_get_home_raises_when_remote_lookup_fails(self, mocker):
        shell = Shell(project, self.remote_machine)
        shell._is_connected = True
        shell._is_local = False
        mocker.patch.object(shell, "run", return_value=(1, [[]], [["boom\n"]]))

        with pytest.raises(RuntimeError):
            shell.get_home()

    def test_copy_to_remote_uses_copy_local_for_local_machine(self, mocker):
        shell = Shell(project, self.local_machine)
        copy_local = mocker.patch.object(shell, "_copy_local", return_value=True)

        assert shell.copy_to_remote("/tmp/src", "/tmp/dst") is True
        copy_local.assert_called_once_with("/tmp/src", "/tmp/dst")

    def test_copy_to_remote_formats_remote_destination(self, mocker):
        shell = Shell(project, self.remote_machine)
        copy_remote = mocker.patch.object(shell, "_copy_remote", return_value=True)

        assert shell.copy_to_remote("/tmp/src", "/tmp/dst") is True
        copy_remote.assert_called_once_with(
            "/tmp/src",
            "user@example.com:/tmp/dst",
            "secret",
            2222,
        )

    def test_copy_to_host_formats_remote_source(self, mocker):
        shell = Shell(project, self.remote_machine)
        copy_remote = mocker.patch.object(shell, "_copy_remote", return_value=True)

        assert shell.copy_to_host("/tmp/src", "/tmp/dst") is True
        copy_remote.assert_called_once_with(
            "user@example.com:/tmp/src",
            "/tmp/dst",
            "secret",
            2222,
        )

    @pytest.mark.parametrize(("return_code", "expected"), [(0, True), (1, False)])
    def test_copy_local_returns_bool_from_cp(self, return_code, expected, mocker):
        shell = Shell(project, self.local_machine)
        mocker.patch("subprocess.call", return_value=return_code)

        assert shell._copy_local("/tmp/src", "/tmp/dst") is expected

    @pytest.mark.parametrize(("return_code", "expected"), [(0, True), (1, False)])
    def test_copy_remote_returns_bool_from_rsync_pwd(
        self, return_code, expected, mocker
    ):
        shell = Shell(project, self.remote_machine)
        call = mocker.patch("subprocess.call", return_value=return_code)

        assert shell._copy_remote("/tmp/src", "/tmp/dst", "secret", 2222) is expected
        args = call.call_args.args[0]
        assert args[:4] == ["sshpass", "-p", "secret", "rsync"]
        assert "--checksum" in args
        assert "--archive" in args

        assert any("ssh" in arg for arg in args)
        assert any("-o StrictHostKeyChecking=no" in arg for arg in args)
        assert any("-o PubkeyAuthentication=no" in arg for arg in args)
        assert any("-o PasswordAuthentication=yes" in arg for arg in args)
        assert any("-o UserKnownHostsFile=/dev/null" in arg for arg in args)
        assert any("-p 2222" in arg for arg in args)

    @pytest.mark.parametrize(("return_code", "expected"), [(0, True), (1, False)])
    def test_copy_remote_returns_bool_from_rsync_key(
        self, return_code, expected, mocker
    ):
        shell = Shell(project, self.remote_machine)
        call = mocker.patch("subprocess.call", return_value=return_code)

        assert shell._copy_remote("/tmp/src", "/tmp/dst", None, 2222) is expected
        args = call.call_args.args[0]
        assert args[:2] == ["sshpass", "rsync"]
        assert "--checksum" in args
        assert "--archive" in args
        assert any("ssh" in arg for arg in args)
        assert any("-o StrictHostKeyChecking=no" in arg for arg in args)
        assert any("-o UserKnownHostsFile=/dev/null" in arg for arg in args)
        assert any("-p 2222" in arg for arg in args)

    def test_set_paranoid_returns_current_level_after_success(self, mocker):
        shell = Shell(project, self.local_machine)
        shell._is_connected = True
        run = mocker.patch.object(
            shell,
            "run",
            side_effect=[
                (0, [[]], [[]]),
                (0, [["-1\n"]], [[]]),
            ],
        )

        assert shell.set_paranoid(-1) == (-1, True)
        assert run.call_args_list[0].args == (
            "echo '-1' > /proc/sys/kernel/perf_event_paranoid",
        )
        assert run.call_args_list[1].args == (
            "cat /proc/sys/kernel/perf_event_paranoid",
        )

    def test_set_paranoid_returns_false_when_read_fails(self, mocker):
        shell = Shell(project, self.local_machine)
        shell._is_connected = True
        mocker.patch.object(
            shell,
            "run",
            side_effect=[
                (1, [[]], [["write failed\n"]]),
                (1, [[]], [["read failed\n"]]),
            ],
        )

        assert shell.set_paranoid(-1) == (0, False)

    @pytest.mark.parametrize("machine", [local_machine])
    def test_copy_to_host(
        self,
        machine: amphimixis.general.MachineInfo,
        tmp_path_factory,
    ):
        shell = amphimixis.Shell(project, machine).connect()

        error, stdout, stderr = shell.run("echo $(mktemp -d)")
        assert error == 0
        remote_tmpdir = stdout[0][0].strip()
        remote_tmpfile = os.path.join(remote_tmpdir, "original.txt")
        shell.run(f"dd if=/dev/random of={remote_tmpfile} bs=1 count=1234")

        local_tmpfile = tmp_path_factory.mktemp("data1") / "original.txt"
        assert shell.copy_to_host(remote_tmpfile, destination=local_tmpfile)

        error, stdout, stderr = shell.run(f"md5sum {remote_tmpfile}")
        assert error == 0
        md5digest_remote = stdout[0][0].split()[0]

        with subprocess.Popen(
            ["md5sum", local_tmpfile],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as cmd:
            assert cmd.wait() == 0
            assert cmd.stdout is not None
            out = cmd.stdout.readline()
            md5digest_local = out.decode("utf-8").split()[0]

        assert md5digest_local == md5digest_remote
