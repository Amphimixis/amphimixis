"""Doxis run subcommand."""

from argparse import Namespace

from amphimixis.amixis.commands.doxis._utils import (
    _image_env,
    _launch,
    _resolve_doxis_script,
)

_REBUILD_SCRIPT_NAME = "build-and-run.sh"
_BUILD_IMAGE_SUBCMD = "build-image"


def _translate_run_args(args: Namespace, list_file: str | None) -> list[str]:
    """Translate parsed args to ``build-and-run.sh`` arguments.

    :param Namespace args: parsed command line arguments
    :param str | None list_file: list file, or None for a build-only run
    :return: argument list for the shell script (without argv[0])
    :rtype: list[str]
    """
    script_args: list[str] = []
    if args.limit:
        script_args += ["--limit", str(args.limit)]
    if args.skip:
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
    for extra in args.extra_docker or []:
        script_args += ["--extra-docker", extra]
    script_args.append(str(list_file))
    return script_args


def _run_pipeline(args: Namespace) -> bool:
    """Run the doxis pipeline, optionally building the image first.

    :param Namespace args: parsed command line arguments
    :return: True if the pipeline succeeded, False otherwise
    :rtype: bool
    """
    if args.target == _BUILD_IMAGE_SUBCMD:
        do_build, list_file = True, args.list_file
    elif args.list_file is not None:
        print(f"error: unexpected argument: {args.list_file}")
        return False
    else:
        do_build, list_file = False, args.target
    if not list_file:
        print("error: list_file is required")
        return False

    env = _image_env(args)

    script = _resolve_doxis_script(_REBUILD_SCRIPT_NAME)
    if script is None:
        print(f"error: missing doxis script {_REBUILD_SCRIPT_NAME}")
        return False
    script_args = _translate_run_args(args, list_file)
    if not do_build:
        script_args = ["--no-build", *script_args]
    return _launch(script, script_args, env)
