# pylint: skip-file
"""Exercise cancellation across the Python, Bash, and Docker-client boundary."""

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from amphimixis.amixis.commands.doxis import _utils


@pytest.mark.unit
@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
@pytest.mark.parametrize("during_startup", [False, True])
def test_launcher_forwards_once_and_restores_handlers(
    mocker, signum, during_startup, capsys
):
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    child = mocker.MagicMock(pid=1234)
    child.__enter__.return_value = child

    def cancel():
        signal.raise_signal(signum)
        signal.raise_signal(signum)

    def spawn(*args, **kwargs):
        if during_startup:
            cancel()
        return child

    def wait(**kwargs):
        if not during_startup:
            cancel()
        return 0

    child.wait.side_effect = wait
    mocker.patch.object(_utils.subprocess, "Popen", side_effect=spawn)
    killpg = mocker.patch.object(_utils.os, "killpg")
    assert _utils._launch(Path("script.sh"), [], {}) is False
    killpg.assert_called_once_with(child.pid, signum)
    assert capsys.readouterr().out.count("Cancelled.") == 1
    assert {sig: signal.getsignal(sig) for sig in previous} == previous


@pytest.mark.unit
def test_launcher_escalates_and_reaps(mocker, capsys):
    child = mocker.MagicMock(pid=1234)
    child.__enter__.return_value = child

    def spawn(*args, **kwargs):
        signal.raise_signal(signal.SIGINT)
        return child

    mocker.patch.object(_utils.subprocess, "Popen", side_effect=spawn)
    mocker.patch.object(_utils.time, "monotonic", side_effect=[10, 41, 46])
    child.wait.side_effect = [
        subprocess.TimeoutExpired("bash", 0.2),
        subprocess.TimeoutExpired("bash", 0.2),
        -signal.SIGKILL,
    ]
    killpg = mocker.patch.object(_utils.os, "killpg")
    assert _utils._launch(Path("script.sh"), [], {}) is False
    assert killpg.call_args_list == [
        mocker.call(1234, signal.SIGINT),
        mocker.call(1234, signal.SIGTERM),
        mocker.call(1234, signal.SIGKILL),
    ]
    assert child.wait.call_count == 3
    assert "removal is unconfirmed" in capsys.readouterr().out


@pytest.mark.unit
def test_launcher_tolerates_child_exit_during_cancellation(mocker):
    child = mocker.MagicMock(pid=1234)
    child.__enter__.return_value = child

    def wait(**kwargs):
        signal.raise_signal(signal.SIGINT)
        return 0

    child.wait.side_effect = wait
    mocker.patch.object(_utils.subprocess, "Popen", return_value=child)
    mocker.patch.object(_utils.os, "killpg", side_effect=ProcessLookupError)
    assert _utils._launch(Path("script.sh"), [], {}) is False


@pytest.mark.unit
def test_launcher_restores_handlers_on_spawn_failure(mocker):
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    mocker.patch.object(
        _utils.subprocess, "Popen", side_effect=FileNotFoundError("bash")
    )
    assert _utils._launch(Path("script.sh"), [], {}) is False
    assert {sig: signal.getsignal(sig) for sig in previous} == previous


@pytest.mark.unit
def test_launcher_does_not_escalate_a_slow_normal_run(mocker):
    child = mocker.MagicMock(pid=1234)
    child.__enter__.return_value = child
    child.wait.side_effect = [subprocess.TimeoutExpired("bash", 0.2), 0]
    mocker.patch.object(_utils.subprocess, "Popen", return_value=child)
    killpg = mocker.patch.object(_utils.os, "killpg")
    assert _utils._launch(Path("script.sh"), [], {}) is True
    killpg.assert_not_called()


@pytest.fixture
def cancellation_harness(tmp_path):
    source = Path(__file__).resolve().parents[1]
    shutil.copytree(
        source / "amphimixis",
        tmp_path / "amphimixis",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    harness = tmp_path / "amphimixis-integrations/doxis"
    harness.mkdir(parents=True)
    for name in ("build-and-run.sh", "process-projects.sh"):
        shutil.copyfile(source / "amphimixis-integrations/doxis" / name, harness / name)
    (harness / "data").mkdir()
    (harness / "data/sample.yml").write_text("test config\n")
    (tmp_path / "projects").write_text("example\nnext-project\n")
    binary_dir = tmp_path / "bin"
    binary_dir.mkdir()
    docker = binary_dir / "docker"
    docker.write_text(
        """#!/bin/bash
set -eu
case "$1" in
  run|build)
    # Simulate a daemon-owned container that outlives an interrupted client.
    trap '' INT
    trap 'exit 0' TERM
    touch "$TEST_ROOT/present"
    printf '%s %s\n' "$$" "$PPID" > "$TEST_ROOT/ready"
    echo "container output"
    while [ -f "$TEST_ROOT/present" ]; do sleep 0.02; done
    ;;
  stop)
    echo stop >> "$TEST_ROOT/events"
    [ "${FAIL_STOP:-0}" = 0 ] || exit 1
    rm -f "$TEST_ROOT/present"
    ;;
  rm)
    if [ -f "$TEST_ROOT/ready" ]; then
      echo rm >> "$TEST_ROOT/events"
      [ "${FAIL_REMOVE:-0}" = 0 ] || exit 1
      [ -f "$TEST_ROOT/present" ] || exit 1
    fi
    rm -f "$TEST_ROOT/present"
    ;;
  container) [ -f "$TEST_ROOT/present" ] ;;
  info) [ "${FAIL_REMOVE:-0}" = 0 ] ;;
esac
"""
    )
    docker.chmod(0o755)
    env = dict(
        os.environ,
        PATH=f"{binary_dir}:/usr/bin:/bin",
        PYTHONPATH=str(tmp_path),
        TEST_ROOT=str(tmp_path),
    )
    # Do not inherit user overrides in an isolated cancellation test.
    env.pop("AMPHIMIXIS_CONTAINER_NAME", None)
    return tmp_path, harness, env


def _wait_for_ready(root, process):
    deadline = time.monotonic() + 5
    ready = root / "ready"
    while time.monotonic() < deadline:
        if ready.exists() and len(ready.read_text().split()) == 2:
            return [int(pid) for pid in ready.read_text().split()]
        assert process.poll() is None, process.communicate(timeout=1)
        time.sleep(0.02)
    pytest.fail("Docker client did not start")


def _cancel_and_check(root, command, env, signum, group=False, expected=1):
    child_group = None
    with subprocess.Popen(
        command,
        cwd=root,
        env=env,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ) as process:
        try:
            docker_pid, runner_pid = _wait_for_ready(root, process)
            child_group = os.getpgid(runner_pid)
            children = (
                Path(f"/proc/{runner_pid}/task/{runner_pid}/children")
                .read_text()
                .split()
            )
            if group:
                os.killpg(process.pid, signum)
            else:
                process.send_signal(signum)
            output, _ = process.communicate(timeout=5)
            assert process.returncode == expected, output
            assert (root / "events").read_text().splitlines() == ["stop", "rm"], output
            assert not (root / "present").exists()
            assert not (
                root / "amphimixis-integrations/doxis/work/next-project_1"
            ).exists()
            assert (root / "amphimixis-integrations/doxis/state").read_text() == ""
            assert not Path(f"/proc/{docker_pid}").exists()
            assert all(not Path(f"/proc/{pid}").exists() for pid in children)
            return output
        finally:
            # Bound failed tests too; these process groups belong to this harness.
            for pgid in {process.pid, child_group} - {None}:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


@pytest.mark.unit
@pytest.mark.parametrize(
    "actions", [["run"], ["run", "build-image"], ["build-image", "run"]]
)
@pytest.mark.parametrize("mode", ["pid-int", "group-int", "pid-term", "resume"])
def test_cli_cancellation_cleans_container(cancellation_harness, actions, mode):
    root, harness, env = cancellation_harness
    # Builds complete normally here; only Docker run blocks.
    docker = root / "bin/docker"
    docker.write_text(docker.read_text().replace("run|build)", "run)"))
    if mode == "resume":
        workspace = root / "existing"
        workspace.mkdir()
        (workspace / "input.yml").write_text("existing config\n")
        (workspace / "pipeline.log").write_text(
            "[entrypoint] opencode: starting pipeline for example (model=test/model)\n"
        )
        selection = ["--resume", str(workspace)]
    else:
        selection = ["projects"]
    command = [sys.executable, "-m", "amphimixis.amixis", "doxis", *actions, *selection]
    signum = signal.SIGTERM if mode == "pid-term" else signal.SIGINT
    output = _cancel_and_check(root, command, env, signum, group=mode == "group-int")
    assert output.count("Cancelled.") == 1
    if mode == "resume":
        assert "starting pipeline" in (workspace / "pipeline.log").read_text()


@pytest.mark.unit
@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
@pytest.mark.parametrize("fail_stop", [False, True])
def test_direct_script_cancellation(cancellation_harness, signum, fail_stop):
    root, harness, env = cancellation_harness
    env["FAIL_STOP"] = str(int(fail_stop))
    command = ["bash", str(harness / "process-projects.sh"), "projects"]
    _cancel_and_check(root, command, env, signum, expected=128 + signum)


@pytest.mark.unit
def test_cli_cancellation_reports_failed_cleanup(cancellation_harness):
    root, harness, env = cancellation_harness
    env.update(FAIL_STOP="1", FAIL_REMOVE="1")
    command = [sys.executable, "-m", "amphimixis.amixis", "doxis", "run", "projects"]
    with subprocess.Popen(
        command,
        cwd=root,
        env=env,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ) as process:
        group = None
        try:
            _, runner_pid = _wait_for_ready(root, process)
            group = os.getpgid(runner_pid)
            process.send_signal(signal.SIGINT)
            output, _ = process.communicate(timeout=5)
            assert process.returncode == 1
            assert "could not confirm removal" in output
        finally:
            for pgid in {process.pid, group} - {None}:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


@pytest.mark.unit
@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_cli_cancels_an_image_build(cancellation_harness, signum):
    root, _, env = cancellation_harness
    docker = root / "bin/docker"
    docker.write_text(
        docker.read_text().replace(
            "trap '' INT\n    trap 'exit 0' TERM",
            "trap 'exit 130' INT\n    trap 'exit 143' TERM",
        )
    )
    command = [sys.executable, "-m", "amphimixis.amixis", "doxis", "build-image"]
    with subprocess.Popen(
        command,
        cwd=root,
        env=env,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    ) as process:
        group = None
        try:
            docker_pid, runner_pid = _wait_for_ready(root, process)
            group = os.getpgid(runner_pid)
            process.send_signal(signum)
            output, _ = process.communicate(timeout=5)
            assert process.returncode == 1, output
            assert "Cancelled." in output
            assert not Path(f"/proc/{docker_pid}").exists()
        finally:
            for pgid in {process.pid, group} - {None}:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
