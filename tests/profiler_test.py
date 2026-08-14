# pylint: skip-file
import subprocess
from pathlib import Path

import pytest
import pytest_mock

from amphimixis.core.profiler import Profiler, general

EXECUTABLE_FILENAME = "a.out"

C_PROGRAM_SUCCESSFUL_RUN = "int main() {return 0;}"
C_PROGRAM_FAILED_RUN = "int main() {return 1;}"
C_PROGRAM_SLEEP_1_SECONDS = "#include <unistd.h>\nint main() {sleep(1); return 0;}"
C_PROGRAM_SLEEP_3_SECONDS = "#include <unistd.h>\nint main() {sleep(3); return 0;}"


@pytest.fixture
def proj_path(tmp_path: Path) -> Path:
    path = tmp_path / "proj_path"
    path.mkdir()
    return path


@pytest.fixture
def build_executable():
    def _build(path: Path, program: str, exec_name: str, build_name: str):
        exec_path = path / build_name / exec_name
        c_program_path = path / "main.c"
        with c_program_path.open("w") as file:
            file.write(program)

        subprocess.run(
            ["gcc", "-o", str(exec_path), str(object=c_program_path)], check=True
        )

    return _build


@pytest.fixture
def get_profiler(mocker: pytest_mock.MockerFixture, monkeypatch: pytest.MonkeyPatch):
    def _profiler(path: Path, exec_name: str) -> Profiler:
        monkeypatch.chdir(path)
        workdir_path_mock = mocker.Mock()
        workdir_path_mock.return_value = str(path)
        mocker.patch("amphimixis.core.Shell.get_project_workdir", workdir_path_mock)
        build = general.Build(
            general.MachineInfo(general.Arch.X86, None, None, None),
            general.MachineInfo(general.Arch.X86, None, None, None),
            "test_build",
            [exec_name],
            None,
            None,
            None,
            None,
        )
        (path / build.build_name).mkdir()

        project = general.Project(str(path), [build])

        profiler_instance = Profiler(project, build)
        perf_record_collect_original = profiler_instance.perf_record_collect

        def wrap(executable, build_path, options="", events=["cycles"]):
            return perf_record_collect_original(
                executable,
                profiler_instance.build_path,
                options,
                events=events,
            )

        mocker.patch.object(profiler_instance, "perf_record_collect", side_effect=wrap)

        return profiler_instance

    return _profiler


@pytest.fixture
def get_shellmocked_profiler(mocker: pytest_mock.MockerFixture, tmp_path: Path):
    def _profiler(executables: list[str] | None = None) -> Profiler:
        build = general.Build(
            general.MachineInfo(general.Arch.X86, None, None, None),
            general.MachineInfo(general.Arch.X86, None, None, None),
            "test_build",
            executables or [EXECUTABLE_FILENAME],
            None,
            None,
            None,
            None,
        )

        project = general.Project(
            str(tmp_path),
            [build],
        )

        shell_mock = mocker.Mock()
        shell_mock.get_project_workdir.return_value = str(tmp_path)
        shell_mock.get_source_dir.return_value = str(tmp_path / "source")
        shell_mock.connect.return_value = shell_mock
        shell_ctor = mocker.patch(
            "amphimixis.core.profiler.shell.Shell", return_value=shell_mock
        )

        profiler = Profiler(project, build)
        assert shell_ctor.called
        return profiler

    return _profiler


@pytest.mark.unit
class TestProfiler:
    @pytest.mark.parametrize(
        "method_name",
        [
            "test_executable",
            "execution_time",
            "perf_stat_collect",
            "perf_record_collect",
        ],
    )
    @pytest.mark.parametrize(
        "program, expected",
        [
            (C_PROGRAM_SUCCESSFUL_RUN, True),
            (C_PROGRAM_FAILED_RUN, False),
        ],
    )
    def test_basic_functions_return_appropriate_value(
        self,
        proj_path,
        get_profiler,
        build_executable,
        method_name: str,
        program: str,
        expected: bool,
    ):
        profiler: Profiler = get_profiler(proj_path, EXECUTABLE_FILENAME)
        build_executable(
            proj_path, program, EXECUTABLE_FILENAME, profiler.build.build_name
        )

        method = getattr(profiler, method_name)

        assert method(EXECUTABLE_FILENAME, profiler.build_path) == expected

    @pytest.mark.parametrize("program", [C_PROGRAM_SUCCESSFUL_RUN])
    def test_execution_time_updates_dictionary_with_correct_data(
        self, proj_path, get_profiler, build_executable, program: str
    ):
        profiler: Profiler = get_profiler(proj_path, EXECUTABLE_FILENAME)
        build_executable(
            proj_path, program, EXECUTABLE_FILENAME, profiler.build.build_name
        )

        assert profiler.execution_time(EXECUTABLE_FILENAME, profiler.build_path)

        for time_counter in (
            "kernel_time",
            "user_time",
            "real_time",
        ):
            assert (
                float(getattr(profiler.stats[EXECUTABLE_FILENAME], time_counter)) >= 0
            )

    @pytest.mark.parametrize(
        "program, expected",
        [
            (C_PROGRAM_SLEEP_1_SECONDS, 1),
            (C_PROGRAM_SLEEP_3_SECONDS, 3),
        ],
    )
    def test_execution_time_measures_right(
        self, proj_path, get_profiler, build_executable, program: str, expected: float
    ):
        profiler: Profiler = get_profiler(proj_path, EXECUTABLE_FILENAME)
        build_executable(
            proj_path, program, EXECUTABLE_FILENAME, profiler.build.build_name
        )

        assert profiler.execution_time(EXECUTABLE_FILENAME, profiler.build_path)
        real_time = profiler.stats[EXECUTABLE_FILENAME].real_time
        assert real_time is not None
        assert float(real_time) > expected - 0.1

    @pytest.mark.parametrize("program", [C_PROGRAM_SUCCESSFUL_RUN])
    def test_perf_data_collect_updates_dictionary_with_some_data_on_successful_run(
        self, proj_path, get_profiler, build_executable, program: str
    ):
        profiler: Profiler = get_profiler(proj_path, EXECUTABLE_FILENAME)
        build_executable(
            proj_path, program, EXECUTABLE_FILENAME, profiler.build.build_name
        )

        assert profiler.perf_stat_collect(EXECUTABLE_FILENAME, profiler.build_path)

        assert profiler.stats[EXECUTABLE_FILENAME].perf_stat is not None

    @pytest.mark.parametrize("program", [C_PROGRAM_SUCCESSFUL_RUN])
    def test_perf_record_collect_creates_valid_perf_data_file(
        self, proj_path, get_profiler, build_executable, program: str
    ):
        profiler: Profiler = get_profiler(proj_path, EXECUTABLE_FILENAME)
        build_executable(
            proj_path, program, EXECUTABLE_FILENAME, profiler.build.build_name
        )

        assert profiler.perf_record_collect(EXECUTABLE_FILENAME, profiler.build_path)

        result = subprocess.run(
            ["perf", "report", "-i", profiler.get_record_filename(EXECUTABLE_FILENAME)],
        )

        assert result.returncode == 0

    @pytest.mark.parametrize("program", [C_PROGRAM_SUCCESSFUL_RUN])
    def test_perf_record_collect_creates_valid_perf_archive_file(
        self, proj_path, get_profiler, build_executable, program: str
    ):
        profiler: Profiler = get_profiler(proj_path, EXECUTABLE_FILENAME)
        build_executable(
            proj_path, program, EXECUTABLE_FILENAME, profiler.build.build_name
        )

        assert profiler.perf_record_collect(EXECUTABLE_FILENAME, profiler.build_path)

        result = subprocess.run(
            [
                "perf",
                "archive",
                "--unpack",
                profiler.get_record_filename(EXECUTABLE_FILENAME),
            ],
        )

        assert result.returncode == 0

    @pytest.mark.parametrize("program", [C_PROGRAM_SUCCESSFUL_RUN])
    def test_profile_all_finds_executables_on_empty_list_in_build(
        self, proj_path, get_profiler, build_executable, program: str
    ):
        profiler: Profiler = get_profiler(proj_path, EXECUTABLE_FILENAME)
        profiler.executables.clear()

        build_executable(
            proj_path, program, EXECUTABLE_FILENAME + "test", profiler.build.build_name
        )

        assert profiler.profile_all(
            profiler.build_path,
            test_executable=False,
            execution_time=False,
            stat_collect=False,
            record_collect=False,
            max_number_of_executables=1,
        )

    @pytest.mark.parametrize("program", [C_PROGRAM_SUCCESSFUL_RUN])
    def test_profile_all_return_false_if_can_not_find_executables(
        self, proj_path, get_profiler, build_executable, program: str
    ):
        profiler: Profiler = get_profiler(proj_path, EXECUTABLE_FILENAME)
        profiler.executables.clear()

        assert not profiler.profile_all(
            profiler.build_path,
            test_executable=False,
            execution_time=False,
            stat_collect=False,
            record_collect=False,
            max_number_of_executables=1,
        )

    @pytest.mark.parametrize("program", [C_PROGRAM_SUCCESSFUL_RUN])
    def test_profile_all_calls_every_method(
        self,
        proj_path,
        get_profiler,
        build_executable,
        mocker: pytest_mock.MockerFixture,
        program: str,
    ):

        profiler: Profiler = get_profiler(proj_path, EXECUTABLE_FILENAME)
        profiler.executables.clear()
        spies = [
            mocker.spy(profiler, "test_executable"),
            mocker.spy(profiler, "execution_time"),
            mocker.spy(profiler, "perf_stat_collect"),
            mocker.spy(profiler, "perf_record_collect"),
        ]

        build_executable(
            proj_path, program, EXECUTABLE_FILENAME + "test", profiler.build.build_name
        )

        profiler.profile_all(
            profiler.build_path,
            test_executable=True,
            execution_time=True,
            stat_collect=True,
            record_collect=True,
            max_number_of_executables=1,
            events=["cycles"],
        )

        assert all(
            s.call_count == 1 for s in spies
        ), "Not all profiler methods were called once"

    @pytest.mark.parametrize(
        "program_fail, program_ok", [(C_PROGRAM_FAILED_RUN, C_PROGRAM_SUCCESSFUL_RUN)]
    )
    def test_profile_all_skips_smoke_test_failed_executables(
        self,
        proj_path,
        get_profiler,
        build_executable,
        mocker: pytest_mock.MockerFixture,
        program_fail: str,
        program_ok: str,
    ):
        profiler: Profiler = get_profiler(proj_path, EXECUTABLE_FILENAME)
        profiler.executables.clear()
        spies = [
            mocker.spy(profiler, "test_executable"),
            mocker.spy(profiler, "execution_time"),
            mocker.spy(profiler, "perf_stat_collect"),
            mocker.spy(profiler, "perf_record_collect"),
        ]

        build_executable(
            proj_path,
            program_fail,
            EXECUTABLE_FILENAME + "fail_test",
            profiler.build.build_name,
        )

        build_executable(
            proj_path,
            program_ok,
            EXECUTABLE_FILENAME + "ok_test",
            profiler.build.build_name,
        )

        profiler.profile_all(
            profiler.build_path,
            test_executable=True,
            execution_time=True,
            stat_collect=True,
            record_collect=True,
            max_number_of_executables=2,
            events=["cycles"],
        )

        assert spies[0].call_count == 2
        assert all(s.call_count == 1 for s in spies[1:])
        failed_stats = profiler.stats[EXECUTABLE_FILENAME + "fail_test"]
        assert failed_stats.executable_run_success is False
        assert failed_stats.real_time is None
        assert failed_stats.user_time is None
        assert failed_stats.kernel_time is None
        assert failed_stats.perf_stat is None
        assert failed_stats.perf_record_name is None
        assert failed_stats.perf_archive_name is None

        passed_stats = profiler.stats[EXECUTABLE_FILENAME + "ok_test"]
        assert passed_stats.executable_run_success is True
        assert passed_stats.real_time is not None
        assert passed_stats.user_time is not None
        assert passed_stats.kernel_time is not None
        assert passed_stats.perf_stat is not None
        assert passed_stats.perf_record_name is not None

    def test_build_cmd_adds_redirects(self, get_shellmocked_profiler):
        profiler: Profiler = get_shellmocked_profiler()

        assert (
            profiler._build_cmd(
                "perf stat -ddd",
                "/tmp/build/a.out",
                stdout_clear=True,
                stderr_clear=True,
            )
            == "perf stat -ddd taskset -c 0 sh -c '/tmp/build/a.out 1>/dev/null 2>/dev/null'"
        )

    def test_perf_stat_command_builds_expected_prompt(self, get_shellmocked_profiler):
        profiler: Profiler = get_shellmocked_profiler()

        assert (
            profiler._perf_stat_command("/tmp/build/a.out", "-d")
            == "perf stat -d -x, taskset -c 0 sh -c '/tmp/build/a.out 2>/dev/null'"
        )

    def test_perf_record_command_builds_expected_prompt(self, get_shellmocked_profiler):
        profiler: Profiler = get_shellmocked_profiler()

        assert (
            profiler._perf_record_command(
                "/tmp/build/a.out", "-g", ["cycles", "branches"]
            )
            == "perf record -g -e cycles,branches taskset -c 0 sh -c '/tmp/build/a.out 2>/dev/null'"
        )

    def test_get_script_command_uses_default_output_filename(
        self, get_shellmocked_profiler
    ):
        profiler: Profiler = get_shellmocked_profiler()
        record_filename = profiler.get_record_filename("bin/a.out")
        script_filename = profiler.get_script_filename("bin/a.out")

        command, filename = profiler._get_script_command(record_filename)

        assert filename == script_filename
        assert (
            command == "perf --no-pager script -F comm,event,ip,sym,dso,period "
            f"-G -i {record_filename} > {script_filename}"
        )

    def test_time_command_keeps_stderr_when_requested(self, get_shellmocked_profiler):
        profiler: Profiler = get_shellmocked_profiler()

        assert (
            profiler._time_command("/tmp/build/a.out", stderr_clear=False)
            == "/bin/time -f\"%e\\n%U\\n%S\" taskset -c 0 sh -c '/tmp/build/a.out'"
        )

    def test_find_executables_returns_empty_list_on_shell_error(
        self, get_shellmocked_profiler, mocker: pytest_mock.MockerFixture
    ):
        profiler: Profiler = get_shellmocked_profiler([])
        mocker.patch.object(
            profiler.shell,
            "run",
            return_value=(1, [[], []], [["find failed\n"]]),
        )

        assert profiler._find_executables(2) == []

    def test_profile_all_uses_source_dir_when_working_directory_not_provided(
        self, get_shellmocked_profiler, mocker: pytest_mock.MockerFixture
    ):
        profiler: Profiler = get_shellmocked_profiler(["bin/a.out"])
        mocker.patch.object(profiler, "test_executable", return_value=True)
        execution = mocker.patch.object(profiler, "execution_time", return_value=True)
        mocker.patch.object(profiler, "perf_stat_collect", return_value=True)
        mocker.patch.object(profiler, "perf_record_collect", return_value=True)
        mocker.patch.object(
            profiler,
            "perf_script",
            return_value=(True, "test_build_bin_a.out.perfdata.scriptout"),
        )

        result = profiler.profile_all()

        assert result == ["bin/a.out"]
        execution.assert_called_once_with("bin/a.out", profiler.shell.get_source_dir())

    def test_profile_all_returns_empty_when_perf_script_fails(
        self, get_shellmocked_profiler, mocker: pytest_mock.MockerFixture
    ):
        profiler: Profiler = get_shellmocked_profiler(["bin/a.out"])
        mocker.patch.object(profiler, "test_executable", return_value=True)
        mocker.patch.object(profiler, "execution_time", return_value=True)
        mocker.patch.object(profiler, "perf_stat_collect", return_value=True)
        mocker.patch.object(profiler, "perf_record_collect", return_value=True)
        mocker.patch.object(profiler, "perf_script", return_value=(False, ""))

        assert profiler.profile_all("/tmp/workdir", events=["cycles"]) == []

    def test_perf_script_returns_false_when_cd_fails(
        self, get_shellmocked_profiler, mocker: pytest_mock.MockerFixture
    ):
        profiler: Profiler = get_shellmocked_profiler()
        record_filename = profiler.get_record_filename("bin/a.out")
        mocker.patch.object(
            profiler.shell,
            "run",
            return_value=(1, [[]], [["cd failed\n"]]),
        )

        assert profiler.perf_script(record_filename, "/tmp/workdir") == (False, "")

    def test_perf_script_returns_false_when_script_command_fails(
        self, get_shellmocked_profiler, mocker: pytest_mock.MockerFixture
    ):
        profiler: Profiler = get_shellmocked_profiler()
        record_filename = profiler.get_record_filename("bin/a.out")
        script_filename = profiler.get_script_filename("bin/a.out")
        mocker.patch.object(
            profiler.shell,
            "run",
            side_effect=[
                (0, [[]], [[]]),
                (1, [[]], [["script failed\n"]]),
            ],
        )

        assert profiler.perf_script(record_filename, "/tmp/workdir") == (False, "")
        assert profiler.cleanup_files == [f"/tmp/workdir/{script_filename}"]

    def test_perf_script_returns_false_when_copy_to_host_fails(
        self, get_shellmocked_profiler, mocker: pytest_mock.MockerFixture
    ):
        profiler: Profiler = get_shellmocked_profiler()
        record_filename = profiler.get_record_filename("bin/a.out")
        mocker.patch.object(
            profiler.shell,
            "run",
            side_effect=[
                (0, [[]], [[]]),
                (0, [[]], [[]]),
            ],
        )
        mocker.patch.object(profiler.shell, "copy_to_host", return_value=False)

        assert profiler.perf_script(record_filename, "/tmp/workdir") == (False, "")

    def test_perf_script_returns_output_filename_on_success(
        self, get_shellmocked_profiler, mocker: pytest_mock.MockerFixture
    ):
        profiler: Profiler = get_shellmocked_profiler()
        record_filename = profiler.get_record_filename("bin/a.out")
        script_filename = profiler.get_script_filename("bin/a.out")
        mocker.patch.object(
            profiler.shell,
            "run",
            side_effect=[
                (0, [[]], [[]]),
                (0, [[]], [[]]),
            ],
        )
        copy_to_host = mocker.patch.object(
            profiler.shell, "copy_to_host", return_value=True
        )

        assert profiler.perf_script(record_filename, "/tmp/workdir") == (
            True,
            script_filename,
        )
        copy_to_host.assert_called_once()

    def test_cleanup_removes_every_file(self, get_shellmocked_profiler, mocker):
        profiler: Profiler = get_shellmocked_profiler()
        profiler.cleanup_files = ["/tmp/a", "/tmp/b"]
        run = mocker.patch.object(profiler.shell, "run")

        profiler.cleanup()

        assert run.call_args_list[0].args == ("rm /tmp/a",)
        assert run.call_args_list[1].args == ("rm /tmp/b",)
