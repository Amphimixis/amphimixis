"""Compare two perf output files."""

# pylint: disable=too-many-arguments

import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
from openai import OpenAI

from amphimixis.core.general import CrossTableFormat, constants, tools
from amphimixis.core.general.tools import get_unique_path


# pylint: disable=too-few-public-methods
class LLMAnalyzer:
    """An OpenAI API wrapper."""

    def __init__(self, api_key=None, base_url=None, model_name=None, project=None):
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv(
            "LLM_BASE_URL", "https://api.openai.com/v1"
        )
        self.model = model_name or os.getenv("LLM_MODEL", "gpt-4o")
        self.project = project or os.getenv("LLM_PROJECT", "")

        self.client = OpenAI(
            api_key=self.api_key, base_url=self.base_url, project=self.project
        )

    def ask(self, system_prompt, user_prompt, temperature=0.2):
        """Send a prompt to the LLM and return the response."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )

        return response.choices[0].message.content


try:
    from amphimixis.core import logger

    _logger = logger.setup_logger("PERF_ANALYZER")
except ImportError:
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    _logger = logging.getLogger("PERF_ANALYZER")

DELTA_COLUMN_LENGTH = 7
LLM_OUTPUT_FILENAME = "perf_llm_output.md"
LLM_SYMBOL_COLUMN_LENGTH = 60
LLM_VALUE_COLUMN_LENGTH = 8


def _parse_perf_line(line):
    parts = line.strip().split()
    if len(parts) < 5:
        _logger.warning("Wrong line format:\n%s", line)
        return None

    period = float(parts[1])
    event_type = parts[2].split(":")[0]
    ip_val = parts[3]

    line_after_ip = line.split(ip_val, 1)[1].strip()
    last_paren_idx = line_after_ip.rfind("(")
    symbol = (
        line_after_ip[:last_paren_idx].strip()
        if last_paren_idx != -1
        else line_after_ip.strip()
    )

    return symbol, period, event_type


def _event_map(event: str) -> str:
    # intel hybrid cpu with E/P cores
    # merges cpu_atom/cycles and cpu_core/cycles into a single 'cycles' event
    # there should be a better solution...
    if "cycles" in event:
        return "cycles"

    # risc-v
    if event == "cpu-clock":
        return "cycles"

    return event


def _get_stats_by_event(filepath):
    # { 'cycles': { 'func1': 100, 'func2': 200 }, 'cache-misses': { ... } }
    event_data = defaultdict(lambda: defaultdict(float))

    try:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                res = _parse_perf_line(line)
                if res:
                    sym, period, ev = res
                    event = _event_map(ev)
                    event_data[event][sym] += period
    except FileNotFoundError:
        return None

    return event_data


INNER_BORDERS = 3
BUILD_TEXT_MARGINS = 2
BUILD_A_DEFAULT = "Build A"
BUILD_B_DEFAULT = "Build B"
PERCENTAGE_MAX_LENGTH = len("100.00")
TOTAL_MARGINS = INNER_BORDERS * BUILD_TEXT_MARGINS


def _get_terminal_width(default: int = 80) -> int:
    """Return terminal width or a fallback value if it cannot be detected."""
    return shutil.get_terminal_size(fallback=(default, 24)).columns


# pylint: disable=too-many-locals
def print_comparison_table(
    event_name, data_a, data_b, max_rows, build_a="Build A", build_b="Build B"
):
    """Print statistics comparison for a specific event."""
    merged = _get_comparison_data(data_a, data_b, max_rows)

    result = merged.reindex(merged.delta.abs().sort_values(ascending=False).index).head(
        max_rows
    )

    if not build_a:
        build_a = "Build A"
    if not build_b:
        build_b = "Build B"

    build_a_column_length = max(
        PERCENTAGE_MAX_LENGTH, len(build_a) + BUILD_TEXT_MARGINS
    )
    build_b_column_length = max(
        PERCENTAGE_MAX_LENGTH, len(build_b) + BUILD_TEXT_MARGINS
    )
    symbol_length = (
        _get_terminal_width()
        - build_a_column_length
        - build_b_column_length
        - DELTA_COLUMN_LENGTH
        - TOTAL_MARGINS
        - INNER_BORDERS
    )

    header_symbol = "Symbol".ljust(symbol_length)
    header_a = f"{build_a} %".rjust(build_a_column_length)
    header_b = f"{build_b} %".rjust(build_b_column_length)
    header_delta = "Delta %".rjust(DELTA_COLUMN_LENGTH)
    event_header = f" EVENT: {event_name.upper()} "

    print(f"\n{event_header.center(_get_terminal_width(), '=')}")
    print(f"{header_symbol} | {header_a} | {header_b} | {header_delta}")
    print("-" * _get_terminal_width())

    for _, row in result.iterrows():
        sym = row["symbol"]
        display_sym = (
            (sym[: symbol_length - 3] + "...") if len(sym) > symbol_length else sym
        )

        val_a = f"{row['share_a']:>{build_a_column_length}.2f}"
        val_b = f"{row['share_b']:>{build_b_column_length}.2f}"
        val_d = f"{row['delta']:>+{DELTA_COLUMN_LENGTH}.2f}"
        print(f"{display_sym.ljust(symbol_length)} | {val_a} | {val_b} | {val_d}")


def _format_df_to_text(event_name, df):
    text = [f"EVENT: {event_name.upper()}"]
    text.append(
        f"{'Symbol':<{LLM_SYMBOL_COLUMN_LENGTH}} | "
        f"{'A%':>{LLM_VALUE_COLUMN_LENGTH}} | "
        f"{'B%':>{LLM_VALUE_COLUMN_LENGTH}} | "
        f"{'Delta%':>{LLM_VALUE_COLUMN_LENGTH}}"
    )
    for _, r in df.iterrows():
        text.append(
            f"{r['symbol'][:LLM_SYMBOL_COLUMN_LENGTH]:<{LLM_SYMBOL_COLUMN_LENGTH}} | "
            f"{r['share_a']:{LLM_VALUE_COLUMN_LENGTH}.2f} | "
            f"{r['share_b']:{LLM_VALUE_COLUMN_LENGTH}.2f} | "
            f"{r['delta']:+{LLM_VALUE_COLUMN_LENGTH}.2f}"
        )
    return "\n".join(text)


def _escape_markdown_text(text: str) -> str:
    """Escape GFM special characters in a text cell."""
    replacements = {
        "\\": "\\\\",
        "_": "\\_",
        "*": "\\*",
        "[": "\\[",
        "]": "\\]",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


# pylint: disable=too-many-locals
def _format_df_to_markdown(
    event_name, df, build_a=BUILD_A_DEFAULT, build_b=BUILD_B_DEFAULT
):
    """Format comparison DataFrame as a GFM markdown table.

    :param str event_name: name of the compared perf event
    :param pd.DataFrame df: comparison data for the event
    :param str build_a: baseline build name
    :param str build_b: another build name
    :return: markdown table text
    :rtype: str
    """
    lines = [f"## EVENT: {_escape_markdown_text(event_name.upper())}", ""]
    headers = ("Symbol", f"{build_a} %", f"{build_b} %", "Delta %")

    rows = []
    for _, r in df.iterrows():
        sym = _escape_markdown_text(str(r["symbol"]))
        val_a = f"{r['share_a']:.2f}"
        val_b = f"{r['share_b']:.2f}"
        val_d = f"{r['delta']:+.2f}"
        rows.append((sym, val_a, val_b, val_d))

    widths = [
        max([len(headers[column])] + [len(row[column]) for row in rows])
        for column in range(len(headers))
    ]

    lines.append(
        "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    )
    lines.append(
        f"|:{'-' * widths[0]}-"
        f"|{'-' * widths[1]}:"
        f"|{'-' * widths[2]}:"
        f"|{'-' * widths[3]}:|"
    )

    for sym, val_a, val_b, val_d in rows:
        lines.append(
            f"| {sym:<{widths[0]}} "
            f"| {val_a:>{widths[1]}} "
            f"| {val_b:>{widths[2]}} "
            f"| {val_d:>{widths[3]}} |"
        )
    return "\n".join(lines) + "\n"


def _get_raw_context(perf_file, target_symbols):
    context_raw = []
    with open(perf_file, encoding="UTF-8") as f:
        for line in f:
            if any(sym in line for sym in target_symbols):
                context_raw.append(line.strip())
            if len(context_raw) > 500:
                break
    return "\n".join(context_raw)


def _get_comparison_data(data_a, data_b, max_rows):
    df_a = pd.DataFrame([{"symbol": s, "weight_a": w} for s, w in data_a.items()])
    df_b = pd.DataFrame([{"symbol": s, "weight_b": w} for s, w in data_b.items()])

    if df_a.empty and df_b.empty:
        return pd.DataFrame()

    if not df_a.empty:
        df_a["share_a"] = (df_a["weight_a"] / df_a["weight_a"].sum()) * 100
    else:
        df_a = pd.DataFrame(columns=["symbol", "share_a"])

    if not df_b.empty:
        df_b["share_b"] = (df_b["weight_b"] / df_b["weight_b"].sum()) * 100
    else:
        df_b = pd.DataFrame(columns=["symbol", "share_b"])

    merged = pd.merge(
        df_a[["symbol", "share_a"]],
        df_b[["symbol", "share_b"]],
        on="symbol",
        how="outer",
    ).fillna(0)

    merged["delta"] = merged["share_b"] - merged["share_a"]

    top_changes = merged.reindex(
        merged.delta.abs().sort_values(ascending=False).index
    ).head(max_rows)

    return top_changes


def _get_build_data(filename: str) -> str:

    if not os.path.exists(filename):
        return ""

    filename = os.path.splitext(filename)[0]

    try:
        return tools.parse_filename(filename)[0]
    except ValueError:
        return ""


def analyze_with_llm(table, samples_a, samples_b):
    """Analyze performance data using a Large Language Model (LLM).

    Save the output to a file.
    """
    analyzer = LLMAnalyzer()
    system_prompt = (
        "Ты — ведущий инженер по производительности систем (Senior Systems Performance Engineer). "
        "Твоя специализация — анализ архитектуры наборов команд (ISA),"
        " микроархитектура процессоров и оптимизация кода на C/C++."
    )

    user_prompt = f"""Проанализируй следующие данные профилирования производительности.
    Используй сборку A (build A) в качестве базовой линии:

    Сводка сравнения сборки A -> сборки B:
    {table}

    Исходные замеры (perf samples) сборки A:
    {samples_a}

    Исходные замеры (perf samples) сборки B:
    {samples_b}

    Задачи:
    1. Выяви основные «горячие точки» (hotspots) в сборке B по сравнению со сборкой A.
    2. Объясни, почему конкретные функции C/C++ могут работать хуже в сборке B 
    (рассмотри вопросы выравнивания данных, атомарные операции или отсутствие специфических инструкций).
    3. Установи корреляцию между промахами кэша (cache-misses) / ошибками предсказания переходов (branch-misses) 
    и деградацией циклов процессора.
    4. Предложи оптимизации на уровне кода или флаги компилятора.
    """

    print("\nАнализ LLM...")
    with open(LLM_OUTPUT_FILENAME, "w", encoding="UTF-8") as f:
        f.write(analyzer.ask(system_prompt, user_prompt))
        print(f"Сохранено в {LLM_OUTPUT_FILENAME}")


def main(
    filename1,
    filename2,
    target_events: None | list[str] = None,
    max_rows=20,
    use_llm=False,
    cross_table_format: CrossTableFormat = CrossTableFormat.ORIGINAL,
) -> int:
    """Compare two perf output files and print the top `max_rows` symbols.

    Print symbols with the most significant changes for specified events.
    Cross-tables are always saved in Markdown to
    ``cross-tables/CT-<first file>-<second file>.md`` independently of the
    console output format.

    :param str filename1: path to baseline build perfdata.scriptout
    :param str filename2: path to another build perfdata.scriptout
    :param list[str] target_events: list of events to compare
    :param int max_rows: maximum symbols to print per event
    :param bool use_llm: use LLM
    :param CrossTableFormat cross_table_format: console output format.
        Default ``CrossTableFormat.ORIGINAL``
    :return: 0 on success, 1 on failure
    :rtype: int
    """
    build_a = _get_build_data(filename1)
    build_b = _get_build_data(filename2)

    if not build_a:
        build_a = BUILD_A_DEFAULT
    if not build_b:
        build_b = BUILD_B_DEFAULT

    stats_a = _get_stats_by_event(filename1)
    stats_b = _get_stats_by_event(filename2)

    if not stats_a or not stats_b:
        return 1

    all_events = sorted(set(stats_a.keys()) | set(stats_b.keys()))

    if not all(event in all_events for event in target_events or []):
        print("Available events: ", *all_events)
        return 1

    top_regressions = []
    comparison_table_text = ""

    file_a_base = os.path.splitext(os.path.basename(filename1))[0]
    file_b_base = os.path.splitext(os.path.basename(filename2))[0]
    md_content = (
        f"# Cross-tables for {_escape_markdown_text(file_a_base)} "
        f"and {_escape_markdown_text(file_b_base)}\n\n"
    )
    if cross_table_format == CrossTableFormat.MARKDOWN:
        print(md_content, end="")

    for event in target_events if target_events else all_events:
        df = _get_comparison_data(stats_a[event], stats_b[event], max_rows)
        md_table = _format_df_to_markdown(event, df, build_a, build_b)

        if cross_table_format == CrossTableFormat.MARKDOWN:
            print(md_table, end="")
        else:
            print_comparison_table(
                event, stats_a[event], stats_b[event], max_rows, build_a, build_b
            )

        comparison_table_text += _format_df_to_text(event, df)
        md_content += md_table + "\n"
        top_regressions.extend(df[df["delta"] > 0.5]["symbol"].tolist())

    raw_samples_a = _get_raw_context(filename1, top_regressions[:5])
    raw_samples_b = _get_raw_context(filename2, top_regressions[:5])
    if use_llm:
        analyze_with_llm(comparison_table_text, raw_samples_a, raw_samples_b)

    _save_cross_tables_md(md_content, file_a_base, file_b_base)

    return 0


def _save_cross_tables_md(md_content, file_a_base, file_b_base) -> None:
    """Save cross-tables markdown to ``cross-tables/CT-<a>-<b>.md``.

    :param str md_content: full markdown content of the cross-tables
    :param str file_a_base: basename of the first compared perf output file
    :param str file_b_base: basename of the second compared perf output file
    """
    safe_name = re.sub(r"[^\w.\-]", "_", f"CT-{file_a_base}-{file_b_base}.md")
    ct_path = get_unique_path(Path(constants.CROSS_TABLES_DIR_NAME) / safe_name)
    ct_path.parent.mkdir(parents=True, exist_ok=True)

    with open(ct_path, "w", encoding="utf-8") as file:
        file.write(md_content)


if __name__ == "__main__":
    if len(sys.argv) < 3 or "-h" in sys.argv or "--help" in sys.argv:
        print(
            "Usage: python3 compare_perf.py "
            "<file1.scriptout> "
            "<file2.scriptout> "
            "[max rows per event]"
        )

        sys.exit(1)

    if len(sys.argv) == 3:
        sys.exit(main(sys.argv[1], sys.argv[2]))
    else:
        sys.exit(main(sys.argv[1], sys.argv[2], None, int(sys.argv[3])))
