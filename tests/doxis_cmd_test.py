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
        "skip": 0,
        "repo": None,
        "config": None,
        "model": None,
        "prompt": None,
        "workdir": None,
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
        "skip": 0,
        "repo": None,
        "config": None,
        "model": None,
        "prompt": None,
        "workdir": None,
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
        assert args.skip == 0
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

    def test_translate_run_args_skips_falsy_limit_skip(self):
        args = _run_args(limit=0, skip=0)
        assert doxis_run._translate_run_args(args, "projects") == ["projects"]

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
    def test_missing_list_file(self):
        assert doxis_cmd.run_doxis(_run_args()) is False

    def test_run_build_image_without_list_fails(self):
        assert doxis_cmd.run_doxis(_run_args(target="build-image")) is False

    def test_unexpected_extra_positional(self):
        assert doxis_cmd.run_doxis(_run_args(target="a", list_file="b")) is False

    def test_run_without_build_adds_no_build(self, mocker, tmp_path):
        list_file = tmp_path / "projects"
        list_file.write_text("util-linux\n")
        rebuild = tmp_path / "rebuild-and-run.sh"
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
        rebuild = tmp_path / "rebuild-and-run.sh"
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
        rebuild = tmp_path / "rebuild-and-run.sh"
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
        rebuild = tmp_path / "rebuild-and-run.sh"
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
        rebuild = tmp_path / "rebuild-and-run.sh"
        rebuild.write_text("#!/usr/bin/env bash\n")
        mocker.patch(
            "amphimixis.amixis.commands.doxis.run._resolve_doxis_script",
            return_value=rebuild,
        )
        mocker.patch("amphimixis.amixis.commands.doxis.run._launch", return_value=False)
        assert doxis_cmd.run_doxis(_run_args(target=str(list_file))) is False

    def test_launch_failure_is_failure(self, mocker, tmp_path):
        rebuild = tmp_path / "rebuild-and-run.sh"
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
        rebuild = doxis_utils._resolve_doxis_script("rebuild-and-run.sh")
        run_sh = doxis_utils._resolve_doxis_script("run.sh")
        assert rebuild is not None and rebuild.name == "rebuild-and-run.sh"
        assert run_sh is not None and run_sh.name == "run.sh"
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
        script = tmp_path / "rebuild-and-run.sh"
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
        assert doxis_utils._launch(tmp_path / "rebuild-and-run.sh", [], {}) is False

    def test_launch_handles_keyboard_interrupt(self, mocker, tmp_path):
        mocker.patch(
            "amphimixis.amixis.commands.doxis._utils.subprocess.run",
            side_effect=KeyboardInterrupt(),
        )
        assert doxis_utils._launch(tmp_path / "rebuild-and-run.sh", [], {}) is False
