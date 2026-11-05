# pylint: skip-file
import subprocess
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from amphimixis.amixis.commands import COMMANDS
from amphimixis.amixis.commands import doxis as doxis_cmd
from amphimixis.amixis.commands.doxis import _utils as doxis_utils
from amphimixis.amixis.commands.doxis import run as doxis_run
from amphimixis.amixis.parser import create_parser


def _run_args(**overrides: Any) -> Namespace:
    base: dict[str, Any] = {
        "doxis_subcommand": "run",
        "target": None,
        "list_file": None,
        "limit": None,
        "skip": None,
        "repo": None,
        "config": None,
        "model": None,
        "prompt": None,
        "workdir": None,
        "resume": None,
        "extra_docker": [],
        "image": None,
    }
    base.update(overrides)
    return Namespace(**base)


def _build_image_args(**overrides: Any) -> Namespace:
    base: dict[str, Any] = {
        "doxis_subcommand": "build-image",
        "target": None,
        "list_file": None,
        "limit": None,
        "skip": None,
        "repo": None,
        "config": None,
        "model": None,
        "prompt": None,
        "workdir": None,
        "resume": None,
        "extra_docker": [],
        "image": None,
    }
    base.update(overrides)
    return Namespace(**base)


@pytest.mark.unit
class TestDoxisArgs:
    def test_registered_in_commands(self):
        assert COMMANDS["doxis"] is doxis_cmd

    def test_bare_doxis_has_no_subcommand(self):
        args = create_parser().parse_args(["doxis"])
        assert args.command == "doxis"
        assert args.doxis_subcommand is None

    def test_bare_doxis_prints_help(self, capsys):
        args = create_parser().parse_args(["doxis"])
        assert doxis_cmd.run_doxis(args) is True
        out = capsys.readouterr().out
        assert "amixis doxis" in out
        assert "run" in out
        assert "build-image" in out

    def test_run_parser_defaults(self):
        args = create_parser().parse_args(["doxis", "run", "projects"])
        assert args.command == "doxis"
        assert args.doxis_subcommand == "run"
        assert args.target == "projects"
        assert args.list_file is None
        assert args.limit is None
        assert args.skip is None
        assert args.prompt is None
        assert args.extra_docker == []
        assert args.image is None

    def test_run_parser_all_flags(self):
        args = create_parser().parse_args(
            [
                "doxis",
                "run",
                "projects",
                "--limit",
                "2",
                "--skip",
                "1",
                "--repo",
                "https://github.com/x/y",
                "--config",
                "cfg.json",
                "--model",
                "opencode/big-pickle",
                "--prompt",
                "do it",
                "--workdir",
                "doxis/work",
                "--extra-docker=--privileged",
                "--extra-docker",
                "-e FOO=1",
                "--image",
                "my-tag",
            ]
        )
        assert args.limit == 2
        assert args.skip == 1
        assert args.repo == "https://github.com/x/y"
        assert args.config == "cfg.json"
        assert args.model == "opencode/big-pickle"
        assert args.prompt == "do it"
        assert args.workdir == "doxis/work"
        assert args.extra_docker == ["--privileged", "-e FOO=1"]
        assert args.image == "my-tag"

    def test_resume_parser_and_translation(self):
        args = create_parser().parse_args(["doxis", "run", "--resume", "existing"])
        assert args.resume == "existing"
        assert doxis_run._translate_run_args(args, None) == [
            "--resume",
            "existing",
        ]

    def test_workspace_flags_are_mutually_exclusive(self):
        with pytest.raises(SystemExit):
            create_parser().parse_args(
                ["doxis", "run", "projects", "--workdir", "new", "--resume", "existing"]
            )

    def test_run_build_image_form(self):
        args = create_parser().parse_args(
            ["doxis", "run", "build-image", "projects", "--limit", "2"]
        )
        assert args.doxis_subcommand == "run"
        assert args.target == "build-image"
        assert args.list_file == "projects"
        assert args.limit == 2

    def test_build_image_parser(self):
        args = create_parser().parse_args(["doxis", "build-image"])
        assert args.doxis_subcommand == "build-image"
        assert args.image is None
        args = create_parser().parse_args(["doxis", "build-image", "--image", "t"])
        assert args.image == "t"

    def test_translate_run_args_all_flags(self):
        args = _run_args(
            limit=2,
            skip=1,
            repo="https://github.com/x/y",
            config="cfg.json",
            model="opencode/big-pickle",
            prompt="do it",
            workdir="doxis/work",
            extra_docker=["--privileged"],
        )
        assert doxis_run._translate_run_args(args, "projects") == [
            "--limit",
            "2",
            "--skip",
            "1",
            "--config",
            "cfg.json",
            "--model",
            "opencode/big-pickle",
            "--prompt",
            "do it",
            "--repo",
            "https://github.com/x/y",
            "--workdir",
            "doxis/work",
            "--extra-docker",
            "--privileged",
            "projects",
        ]

    def test_translate_run_args_minimal(self):
        assert doxis_run._translate_run_args(_run_args(), "projects") == ["projects"]

    def test_translate_run_args_preserves_explicit_zero_selection(self):
        args = _run_args(limit=0, skip=0)
        assert doxis_run._translate_run_args(args, "projects") == [
            "--limit",
            "0",
            "--skip",
            "0",
            "projects",
        ]

    def test_translate_run_args_multiple_extra_docker(self):
        args = _run_args(extra_docker=["--privileged", "-e FOO=1"])
        assert doxis_run._translate_run_args(args, "projects") == [
            "--extra-docker",
            "--privileged",
            "--extra-docker",
            "-e FOO=1",
            "projects",
        ]


@pytest.mark.unit
class TestRunDoxis:
    @pytest.mark.parametrize("build", [False, True])
    def test_resume_launches_without_list(self, mocker, build):
        mocker.patch(
            "amphimixis.amixis.commands.doxis.run._resolve_doxis_script",
            return_value=Path("build-and-run.sh"),
        )
        launch = mocker.patch(
            "amphimixis.amixis.commands.doxis.run._launch", return_value=True
        )
        args = create_parser().parse_args(
            [
                "doxis",
                "run",
                *(["build-image"] if build else []),
                "--resume",
                "existing",
            ]
        )
        assert doxis_cmd.run_doxis(args) is True
        expected = ([] if build else ["--no-build"]) + ["--resume", "existing"]
        assert launch.call_args.args[1] == expected

    @pytest.mark.parametrize(
        "selection", [["projects"], ["--limit", "0"], ["--skip", "0"]]
    )
    def test_resume_rejects_project_selection(self, mocker, selection):
        launch = mocker.patch("amphimixis.amixis.commands.doxis.run._launch")
        args = create_parser().parse_args(
            ["doxis", "run", *selection, "--resume", "existing"]
        )
        assert doxis_cmd.run_doxis(args) is False
        launch.assert_not_called()

    def test_missing_list_file(self):
        assert doxis_cmd.run_doxis(_run_args()) is False

    def test_run_build_image_without_list_fails(self):
        assert doxis_cmd.run_doxis(_run_args(target="build-image")) is False

    def test_unexpected_extra_positional(self):
        assert doxis_cmd.run_doxis(_run_args(target="a", list_file="b")) is False

    def test_run_without_build_adds_no_build(self, mocker, tmp_path):
        list_file = tmp_path / "projects"
        list_file.write_text("util-linux\n")
        rebuild = tmp_path / "build-and-run.sh"
        rebuild.write_text("#!/usr/bin/env bash\n")
        mocker.patch(
            "amphimixis.amixis.commands.doxis.run._resolve_doxis_script",
            return_value=rebuild,
        )
        launch_mock = mocker.patch(
            "amphimixis.amixis.commands.doxis.run._launch", return_value=True
        )
        args = _run_args(target=str(list_file), image="my-tag", limit=1)
        assert doxis_cmd.run_doxis(args) is True
        (script, script_args, env), _ = launch_mock.call_args
        assert script == rebuild
        assert script_args[0] == "--no-build"
        assert script_args[-1] == str(list_file)
        assert "--limit" in script_args
        assert "1" in script_args
        assert "--no-run" not in script_args
        assert env["AMPHIMIXIS_IMAGE"] == "my-tag"

    def test_run_build_image_calls_rebuild_script(self, mocker, tmp_path):
        list_file = tmp_path / "projects"
        list_file.write_text("util-linux\n")
        rebuild = tmp_path / "build-and-run.sh"
        rebuild.write_text("#!/usr/bin/env bash\n")
        mocker.patch(
            "amphimixis.amixis.commands.doxis.run._resolve_doxis_script",
            return_value=rebuild,
        )
        launch_mock = mocker.patch(
            "amphimixis.amixis.commands.doxis.run._launch", return_value=True
        )
        args = _run_args(target="build-image", list_file=str(list_file))
        assert doxis_cmd.run_doxis(args) is True
        (script, script_args, _env), _ = launch_mock.call_args
        assert script == rebuild
        assert script_args[-1] == str(list_file)
        assert "--no-build" not in script_args
        assert "--no-run" not in script_args

    def test_run_parser_build_image_form_launches_without_no_build(
        self, mocker, tmp_path
    ):
        list_file = tmp_path / "projects"
        list_file.write_text("util-linux\n")
        rebuild = tmp_path / "build-and-run.sh"
        rebuild.write_text("#!/usr/bin/env bash\n")
        mocker.patch(
            "amphimixis.amixis.commands.doxis.run._resolve_doxis_script",
            return_value=rebuild,
        )
        launch_mock = mocker.patch(
            "amphimixis.amixis.commands.doxis.run._launch", return_value=True
        )
        args = create_parser().parse_args(
            [
                "doxis",
                "run",
                "build-image",
                str(list_file),
                "--limit",
                "2",
                "--image",
                "my-tag",
            ]
        )
        assert doxis_cmd.run_doxis(args) is True
        (script, script_args, env), _ = launch_mock.call_args
        assert script == rebuild
        assert "--no-build" not in script_args
        assert "--no-run" not in script_args
        assert script_args[-1] == str(list_file)
        assert env["AMPHIMIXIS_IMAGE"] == "my-tag"

    def test_build_image_calls_rebuild_no_run(self, mocker, tmp_path):
        rebuild = tmp_path / "build-and-run.sh"
        rebuild.write_text("#!/usr/bin/env bash\n")
        mocker.patch(
            "amphimixis.amixis.commands.doxis.build_image._resolve_doxis_script",
            return_value=rebuild,
        )
        launch_mock = mocker.patch(
            "amphimixis.amixis.commands.doxis.build_image._launch", return_value=True
        )
        assert doxis_cmd.run_doxis(_build_image_args(image="t")) is True
        (script, script_args, env), _ = launch_mock.call_args
        assert script == rebuild
        assert script_args == ["--no-run"]
        assert env["AMPHIMIXIS_IMAGE"] == "t"

    def test_build_image_script_missing(self, mocker):
        mocker.patch(
            "amphimixis.amixis.commands.doxis.build_image._resolve_doxis_script",
            return_value=None,
        )
        assert doxis_cmd.run_doxis(_build_image_args()) is False

    def test_script_missing(self, mocker, tmp_path):
        list_file = tmp_path / "projects"
        list_file.write_text("util-linux\n")
        mocker.patch(
            "amphimixis.amixis.commands.doxis.run._resolve_doxis_script",
            return_value=None,
        )
        assert doxis_cmd.run_doxis(_run_args(target=str(list_file))) is False

    def test_nonzero_rc_is_failure(self, mocker, tmp_path):
        list_file = tmp_path / "projects"
        list_file.write_text("util-linux\n")
        rebuild = tmp_path / "build-and-run.sh"
        rebuild.write_text("#!/usr/bin/env bash\n")
        mocker.patch(
            "amphimixis.amixis.commands.doxis.run._resolve_doxis_script",
            return_value=rebuild,
        )
        mocker.patch("amphimixis.amixis.commands.doxis.run._launch", return_value=False)
        assert doxis_cmd.run_doxis(_run_args(target=str(list_file))) is False

    def test_launch_failure_is_failure(self, mocker, tmp_path):
        rebuild = tmp_path / "build-and-run.sh"
        rebuild.write_text("#!/usr/bin/env bash\n")
        mocker.patch(
            "amphimixis.amixis.commands.doxis.build_image._resolve_doxis_script",
            return_value=rebuild,
        )
        mocker.patch(
            "amphimixis.amixis.commands.doxis.build_image._launch", return_value=False
        )
        assert doxis_cmd.run_doxis(_build_image_args()) is False

    def test_resolve_scripts_from_repo(self):
        rebuild = doxis_utils._resolve_doxis_script("build-and-run.sh")
        run_sh = doxis_utils._resolve_doxis_script("process-projects.sh")
        assert rebuild is not None and rebuild.name == "build-and-run.sh"
        assert run_sh is not None and run_sh.name == "process-projects.sh"
        assert rebuild.parent == run_sh.parent
        assert doxis_utils._resolve_doxis_script("no-such-script.sh") is None

    def test_image_env_override(self):
        env = doxis_utils._image_env(_run_args(image="my-tag"))
        assert env["AMPHIMIXIS_IMAGE"] == "my-tag"

    def test_image_env_keeps_parent_env(self, mocker):
        mocker.patch.dict("os.environ", {"KEEP_ME": "1"}, clear=False)
        env = doxis_utils._image_env(_run_args())
        assert env["KEEP_ME"] == "1"
        assert "AMPHIMIXIS_IMAGE" not in env

    def test_launch_reports_returncode(self, mocker, tmp_path):
        script = tmp_path / "build-and-run.sh"
        script.write_text("#!/usr/bin/env bash\n")
        for returncode, expected in ((0, True), (2, False)):
            completed = subprocess.CompletedProcess(
                args=["bash", str(script)], returncode=returncode
            )
            run_mock = mocker.patch(
                "amphimixis.amixis.commands.doxis._utils.subprocess.run",
                return_value=completed,
            )
            assert (
                doxis_utils._launch(script, ["--no-run"], {"AMPHIMIXIS_IMAGE": "t"})
                is expected
            )
            run_mock.assert_called_once_with(
                ["bash", str(script), "--no-run"],
                env={"AMPHIMIXIS_IMAGE": "t"},
                check=False,
            )

    def test_launch_handles_missing_bash(self, mocker, tmp_path):
        mocker.patch(
            "amphimixis.amixis.commands.doxis._utils.subprocess.run",
            side_effect=FileNotFoundError("bash"),
        )
        assert doxis_utils._launch(tmp_path / "build-and-run.sh", [], {}) is False

    def test_launch_handles_keyboard_interrupt(self, mocker, tmp_path):
        mocker.patch(
            "amphimixis.amixis.commands.doxis._utils.subprocess.run",
            side_effect=KeyboardInterrupt(),
        )
        assert doxis_utils._launch(tmp_path / "build-and-run.sh", [], {}) is False


@pytest.fixture
def doxis_harness(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[1] / "amphimixis-integrations/doxis"
    harness = tmp_path / "doxis"
    harness.mkdir()
    for name in ("process-projects.sh", "build-and-run.sh"):
        (harness / name).write_text((source / name).read_text())
    (harness / "data").mkdir()
    (harness / "data/sample.yml").write_text("fresh config\n")
    projects = tmp_path / "projects"
    projects.write_text("example\n")
    docker = tmp_path / "docker"
    docker.write_text(
        "#!/bin/bash\n"
        'if [ "$1" = run ]; then\n'
        '  printf "%s\\n" "$@" > "$DOCKER_CALL"\n'
        '  echo "new pipeline output"\n'
        "  exit 7\n"
        "fi\n"
    )
    docker.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    monkeypatch.setenv("DOCKER_CALL", str(tmp_path / "docker-call"))
    return harness, projects, tmp_path / "docker-call"


@pytest.mark.unit
@pytest.mark.parametrize("project_names", ["example\n", "example\nsecond\n"])
def test_workdir_always_creates_numbered_workspaces(
    doxis_harness, tmp_path, project_names
):
    harness, projects, docker_call = doxis_harness
    projects.write_text(project_names)
    parent = tmp_path / "custom workspaces"
    (parent / "example_1").mkdir(parents=True)
    result = subprocess.run(
        [
            "bash",
            str(harness / "build-and-run.sh"),
            str(projects),
            "--no-build",
            "--workdir",
            str(parent),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    for project in project_names.split():
        workspace = parent / ("example_2" if project == "example" else "second_1")
        assert (workspace / "input.yml").read_text() == "fresh config\n"
        assert "new pipeline output" in (workspace / "pipeline.log").read_text()
    assert "RESUME=1" not in docker_call.read_text()
    assert "container exit: 7" in result.stdout


@pytest.mark.unit
@pytest.mark.parametrize("script_name", ["build-and-run.sh", "process-projects.sh"])
@pytest.mark.parametrize("override", [False, True])
def test_resume_preserves_workspace_and_forwards_mode(
    doxis_harness, tmp_path, script_name, override
):
    harness, _, docker_call = doxis_harness
    workspace = tmp_path / "existing workspace"
    workspace.mkdir()
    (workspace / "input.yml").write_text("custom config\n")
    (workspace / "pipeline.log").write_text(
        "previous actions\n"
        "[entrypoint] opencode: starting pipeline for old (model=old/model)\n"
        "other output\n"
        "2026-11-05 14:21:37 [entrypoint] opencode: starting pipeline for "
        "util-linux (model=opencode/big-pickle)\n"
        "later output\n"
    )
    (harness / "state").write_text("util-linux\n")
    # Resume must not depend on the original template still being available.
    (harness / "data/sample.yml").unlink()
    result = subprocess.run(
        [
            "bash",
            str(harness / script_name),
            *(["--no-build"] if script_name == "build-and-run.sh" else []),
            "--resume",
            str(workspace),
            *(["--model", "custom/model"] if override else []),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (workspace / "input.yml").read_text() == "custom config\n"
    log = (workspace / "pipeline.log").read_text()
    assert log.startswith("previous actions\n")
    assert "new pipeline output" in log
    assert "RESUME=1" in docker_call.read_text()
    assert "PROJECT_NAME=util-linux" in docker_call.read_text()
    expected_model = "custom/model" if override else "opencode/big-pickle"
    assert f"MODEL={expected_model}" in docker_call.read_text()
    assert f"{workspace}:/work" in docker_call.read_text()
    assert "container exit: 7" in result.stdout


@pytest.mark.unit
@pytest.mark.parametrize("script_name", ["build-and-run.sh", "process-projects.sh"])
@pytest.mark.parametrize(
    "invalid",
    [
        "missing-log",
        "missing-input",
        "missing-metadata",
        "malformed-metadata",
        "list-file",
        "limit",
        "skip",
        "workdir",
    ],
)
def test_resume_rejects_invalid_workspace_selection(
    doxis_harness, tmp_path, invalid, script_name
):
    harness, projects, docker_call = doxis_harness
    workspace = tmp_path / "existing"
    workspace.mkdir()
    if invalid != "missing-input":
        (workspace / "input.yml").write_text("config\n")
    log = workspace / "pipeline.log"
    if invalid != "missing-log":
        content = "[entrypoint] opencode: starting pipeline for example (model=p/m)\n"
        if invalid == "missing-metadata":
            content = "previous actions\n"
        elif invalid == "malformed-metadata":
            content = "[entrypoint] opencode: starting pipeline for  (model=)\n"
        log.write_text(content)
    before = {p.name: p.read_bytes() for p in workspace.iterdir()}
    args = ["--resume", str(workspace)]
    if invalid == "list-file":
        args += [str(projects)]
    elif invalid in ("limit", "skip"):
        args += [f"--{invalid}", "0"]
    elif invalid == "workdir":
        args += ["--workdir", str(tmp_path / "new")]
    result = subprocess.run(
        ["bash", str(harness / script_name), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "--resume" in result.stderr
    assert not docker_call.exists()
    assert {p.name: p.read_bytes() for p in workspace.iterdir()} == before
    assert not (harness / "state").exists()
    assert not (tmp_path / "new").exists()


@pytest.mark.unit
@pytest.mark.parametrize("resume", [False, True])
def test_entrypoint_prompt_recovers_history_only_on_resume(
    tmp_path, monkeypatch, resume
):
    source = (
        Path(__file__).resolve().parents[1]
        / "amphimixis-integrations/doxis/docker-entrypoint.sh"
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "pipeline.log").write_text("previous actions\n")
    # Run the real prompt construction with container-only paths redirected.
    script = source.read_text().replace("/work", str(workspace))
    script = "\n".join(
        line
        for line in script.splitlines()
        if "/proc/sys/kernel/perf_event_paranoid" not in line
    )
    entrypoint = tmp_path / "entrypoint.sh"
    entrypoint.write_text(script)
    for name, body in (
        ("opencode", 'printf "%s\\n" "$@" > "$PROMPT_CAPTURE"'),
        ("chown", "exit 0"),
    ):
        executable = tmp_path / name
        executable.write_text(f"#!/bin/bash\n{body}\n")
        executable.chmod(0o755)
    capture = tmp_path / "prompt"
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    monkeypatch.setenv("PROJECT_NAME", "example")
    monkeypatch.setenv("PROJECT_REPO", "https://github.com/x/y")
    monkeypatch.setenv("PIPELINE_PROMPT", "additional task")
    monkeypatch.setenv("RESUME", "1" if resume else "0")
    monkeypatch.setenv("PROMPT_CAPTURE", str(capture))
    result = subprocess.run(
        ["bash", str(entrypoint)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    prompt = capture.read_text()
    assert "additional task" in prompt
    if resume:
        assert f"read {workspace}/pipeline.log" in prompt
        assert "already performed actions" in prompt
        assert "continue from the first unfinished phase" in prompt
        assert "Clone exactly" not in prompt
        assert "Do not read pipeline.log" not in prompt
    else:
        assert "Do not read pipeline.log" in prompt
        assert "Clone exactly" in prompt
