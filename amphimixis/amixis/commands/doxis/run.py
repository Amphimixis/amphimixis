"""Doxis run subcommand."""

from argparse import Namespace

from amphimixis.amixis.commands.doxis._utils import (
    _image_env,
    _launch,
    _resolve_doxis_script,
)

_REBUILD_SCRIPT_NAME = "build-and-run.sh"


def _translate_run_args(args: Namespace, list_file: str | None) -> list[str]:
    """Translate parsed args to ``build-and-run.sh`` arguments.

    :param Namespace args: parsed command line arguments
    :param str | None list_file: list file, or None when resuming
    :return: argument list for the shell script (without argv[0])
    :rtype: list[str]
    """
    script_args: list[str] = []
    if args.limit is not None:
        script_args += ["--limit", str(args.limit)]
    if args.skip is not None:
        script_args += ["--skip", str(args.skip)]
    if args.config:
        script_args += ["--config", str(args.config)]
    if args.model:
        script_args += ["--model", str(args.model)]
    if args.prompt:
        script_args += ["--prompt", str(args.prompt)]
    if args.repo:
        script_args += ["--repo", str(args.repo)]
    if getattr(args, "workdir", None):
        script_args += ["--workdir", str(args.workdir)]
    if getattr(args, "resume", None):
        script_args += ["--resume", str(args.resume)]
    for extra in args.extra_docker or []:
        script_args += ["--extra-docker", extra]
    if list_file is not None:
        script_args.append(list_file)
    return script_args


def _run_pipeline(args: Namespace, *, build_image: bool) -> bool:
    """Run the doxis pipeline, optionally building the image first.

    :param Namespace args: parsed command line arguments
    :param bool build_image: whether to build the image before running
    :return: True if the pipeline succeeded, False otherwise
    :rtype: bool
    """
    list_file = args.list_file
    if getattr(args, "resume", None):
        if not _validate_resume_args(args, list_file):
            return False
    elif not list_file:
        print("error: list_file is required")
        return False

    env = _image_env(args)

    script = _resolve_doxis_script(_REBUILD_SCRIPT_NAME)
    if script is None:
        print(f"error: missing doxis script {_REBUILD_SCRIPT_NAME}")
        return False
    script_args = _translate_run_args(args, list_file)
    if not build_image:
        script_args = ["--no-build", *script_args]
    return _launch(script, script_args, env)


def _validate_resume_args(args: Namespace, list_file: str | None) -> bool:
    """Reject project selection arguments when resuming from log metadata."""
    if (
        list_file is not None
        or args.limit is not None
        or args.skip is not None
        or args.workdir is not None
    ):
        print(
            "error: --resume cannot be combined with a list file, "
            "--limit, --skip, or --workdir"
        )
        return False
    return True
