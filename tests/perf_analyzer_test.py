# pylint: skip-file
import json
from pathlib import Path

import pytest
import pytest_mock
import yaml

import amphimixis.core.perf_analyzer as perf_analyzer
from amphimixis.core.general import (
    Arch,
    Build,
    CrossTableFormat,
    MachineInfo,
    ProfileStats,
    Project,
    StatsFileFormat,
    tools,
)
from amphimixis.core.profiler import Profiler

RAW_PERF_STAT = (
    "1153848||cycles|1100000|100.00|||\n"
    "47233||cache-misses|1100000|100.00|0.04|M/sec|"
)

SCRIPT_LINES_A = (
    "main 100 cycles:ppp 400000 ffffffff main (app)\n"
    "main 300 cache-misses:ppp 400000 ffffffff main (app)\n"
)
SCRIPT_LINES_B = (
    "main 100 cpu-clock:ppp 400000 ffffffff main (app)\n"
    "main 500 cache-misses:ppp 400000 ffffffff main (app)\n"
)


@pytest.fixture
def scriptout_files(tmp_path: Path) -> tuple[str, str]:
    file_a = tmp_path / "1_1_1..bin_app.scriptout"
    file_b = tmp_path / "2_2_2..bin_app.scriptout"
    file_a.write_text(SCRIPT_LINES_A, encoding="utf-8")
    file_b.write_text(SCRIPT_LINES_B, encoding="utf-8")
    return str(file_a), str(file_b)


@pytest.mark.unit
def test_parse_perf_stat_csv() -> None:
    lines = [
        "# started on Mon Aug 24 10:00:00 2026",
        "1153848 || cycles | 1100000 | 100.00 | | |",
        "",
        "47233 || cache-misses | 1100000 | 100.00 | 0.04 | M/sec | ",
    ]

    parsed = Profiler._parse_perf_stat_csv(lines)

    assert len(parsed) == 2
    assert parsed[0]["counter_value"] == "1153848"
    assert parsed[0]["event"] == "cycles"
    assert "metric-unit" not in parsed[0]
    assert parsed[1]["event"] == "cache-misses"
    assert parsed[1]["metric-value"] == "0.04"
    assert parsed[1]["metric-unit"] == "M/sec"


@pytest.mark.unit
def test_serialize_stats_converts_perf_stat_to_dicts() -> None:
    merged = {
        "build1": {
            "a.out": ProfileStats(
                build_name="build1",
                executable="a.out",
                perf_stat=RAW_PERF_STAT,
            )
        }
    }

    serialized = Profiler._serialize_stats(merged)

    perf_stat = serialized["build1"]["a.out"]["perf_stat"]
    assert isinstance(perf_stat, list)
    assert perf_stat[0]["event"] == "cycles"

    without_stat = Profiler._serialize_stats({"build1": {"a.out": ProfileStats()}})
    assert without_stat["build1"]["a.out"]["perf_stat"] is None


@pytest.fixture
def get_stats_profiler(mocker: pytest_mock.MockerFixture, tmp_path: Path):
    def _profiler(project_name: str = "myproj") -> Profiler:
        build = Build(
            MachineInfo(Arch.X86, None, None),
            MachineInfo(Arch.X86, None, None),
            "test_build",
            ["a.out"],
            None,
            None,
            None,
            None,
        )
        project = Project(str(tmp_path / project_name), [build])

        shell_mock = mocker.Mock()
        shell_mock.connect.return_value = shell_mock
        shell_mock.get_project_workdir.return_value = str(tmp_path)
        mocker.patch("amphimixis.core.profiler.shell.Shell", return_value=shell_mock)
        return Profiler(project, build)

    return _profiler


@pytest.mark.unit
def test_save_stats_json_and_pickle(
    get_stats_profiler, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    profiler = get_stats_profiler()
    profiler.stats["a.out"] = ProfileStats(
        build_name="test_build",
        executable="a.out",
        executable_run_success=True,
        perf_stat=RAW_PERF_STAT,
    )

    profiler.save_stats()

    pickle_file = tmp_path / "myproj.pkl"
    json_file = tmp_path / "myproj.json"
    assert pickle_file.is_file()
    assert json_file.is_file()

    loaded: dict = tools.load_project_stats(profiler.project)
    assert loaded["test_build"]["a.out"].perf_stat == RAW_PERF_STAT

    readable = json.loads(json_file.read_text(encoding="utf-8"))
    perf_stat = readable["test_build"]["a.out"]["perf_stat"]
    assert perf_stat[0]["event"] == "cycles"


@pytest.mark.unit
def test_save_stats_yaml(
    get_stats_profiler, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    profiler = get_stats_profiler()
    profiler.stats["a.out"] = ProfileStats(
        build_name="test_build", executable="a.out", real_time="0.01"
    )

    profiler.save_stats(stats_file_format=StatsFileFormat.YAML)

    yaml_file = tmp_path / "myproj.yaml"
    assert not (tmp_path / "myproj.json").exists()
    readable = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
    assert readable["test_build"]["a.out"]["real_time"] == "0.01"
    assert readable["test_build"]["a.out"]["perf_stat"] is None


@pytest.mark.unit
def test_format_df_to_markdown_escapes_symbols() -> None:
    data_a = {"my_func": 100}
    data_b = {"my_func": 300, "other*func[1]": 50}

    df = perf_analyzer._get_comparison_data(data_a, data_b, 20)
    md = perf_analyzer._format_df_to_markdown("cache-misses", df, "A", "B")

    assert md.startswith("## EVENT: CACHE-MISSES\n")
    assert "| Symbol" in md
    assert "| A %" in md
    assert "| B %" in md
    assert "| Delta %" in md
    assert "|:---" in md
    assert "my\\_func" in md
    assert "other\\*func\\[1\\]" in md
    assert "+14.29" in md
    assert "-14.29" in md


@pytest.mark.unit
def test_compare_saves_markdown_in_original_mode(
    scriptout_files, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)

    assert perf_analyzer.main(*scriptout_files) == 0

    ct_files = list((tmp_path / "cross-tables").glob("CT-*.md"))
    assert len(ct_files) == 1
    content = ct_files[0].read_text(encoding="utf-8")
    assert content.startswith("# Cross-tables for ")
    assert "## EVENT: CACHE-MISSES" in content

    captured = capsys.readouterr().out
    assert "EVENT: CACHE-MISSES" in captured
    assert "| Symbol" not in captured


@pytest.mark.unit
def test_compare_prints_and_saves_markdown(
    scriptout_files: tuple[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert (
        perf_analyzer.main(
            scriptout_files[0],
            scriptout_files[1],
            cross_table_format=CrossTableFormat.MARKDOWN,
        )
        == 0
    )

    ct_files = list((tmp_path / "cross-tables").glob("CT-*.md"))
    assert len(ct_files) == 1

    captured = capsys.readouterr().out
    assert "# Cross-tables for 1\\_1\\_1..bin\\_app" in captured
    assert "| Symbol" in captured
