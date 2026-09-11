#!/usr/bin/env python3
"""Generate the softened Amphimixis agents used inside the Docker image."""

from pathlib import Path

SOURCE_DIR = Path(__file__).resolve().parents[3] / ".opencode" / "agents"
AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents-docker"
PATTERN = "amphimixis*.md"


def soften(path: Path) -> None:
    """Replace the ``bash:`` pattern block with ``"*": allow`` in one file."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    output: list[str] = []
    inside_bash = False
    for line in lines:
        if not inside_bash and line.rstrip("\n") == "  bash:":
            inside_bash = True
            output.append(line)
            continue
        if inside_bash:
            if line.startswith("    "):
                continue
            output.append('    "*": allow\n')
            inside_bash = False
        output.append(line)
    path.write_text("".join(output), encoding="utf-8")


def copy_agent(src: Path) -> Path:
    """Copy one strict agent into agents-docker and return the copy."""
    target = AGENTS_DIR / src.name
    target.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def main() -> int:
    """Copy the host agents and soften each in the container agents dir."""
    sources = sorted(SOURCE_DIR.glob(PATTERN))
    if not sources:
        print(f"no agent files found in {SOURCE_DIR}")
        return 1
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    for src in sources:
        soften(copy_agent(src))
        print(f"copied and softened: {src.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
