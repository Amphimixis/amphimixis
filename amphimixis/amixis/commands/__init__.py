"""CLI commands package."""

from amphimixis.amixis.commands import (
    add,
    analyze,
    build,
    clean,
    compare,
    doxis,
    init,
    opencode,
    profile,
    run,
    validate,
)

COMMANDS = {
    "add": add,
    "analyze": analyze,
    "build": build,
    "clean": clean,
    "compare": compare,
    "doxis": doxis,
    "init": init,
    "opencode": opencode,
    "profile": profile,
    "run": run,
    "validate": validate,
}
