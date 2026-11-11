from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from .notebook_builder import build, build_default


def _options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", default="notebooks", help="Notebook file or source directory")
    parser.add_argument("--output", default="build", help="Output directory")
    parser.add_argument("--prefix", default="dev_", help="Source filename prefix")
    parser.add_argument("--execute", action="store_true", help="Execute cleaned notebooks using nbclient")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and check cleaned notebooks.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "check"):
        command = commands.add_parser(name, help=f"{name.capitalize()} notebooks")
        _options(command)
        if name == "build":
            command.add_argument("--check", action="store_true", help="Validate without writing")
    commands.add_parser("doctor", help="Report optional notebook dependencies")
    return parser


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if Path(sys.argv[0]).name == "load-clean-build":
        args_list.insert(0, "build")
    parser = create_parser()
    args = parser.parse_args(args_list)
    if args.command == "doctor":
        print(f"Python: {sys.executable}")
        print("sys.path:")
        for entry in sys.path:
            print(f"  {entry or '(current directory)'}")
        missing = []
        for name in ("nbformat", "jupytext", "nbclient", "IPython", "ipykernel"):
            available = importlib.util.find_spec(name) is not None
            print(f"{name}: {'available' if available else 'missing'}")
            if not available:
                missing.append(name)
        if missing:
            print("Install notebook tools with pip install 'load-clean[tools]'; install nbclient and an IPython kernel for --execute.")
        return 0
    try:
        source = Path(args.source)
        if not source.exists():
            raise FileNotFoundError(f"Source does not exist: {source}")
        check = args.command == "check" or getattr(args, "check", False)
        kwargs = dict(output=args.output, prefix=args.prefix, execute=args.execute, check=check)
        paths = [build(source, **kwargs)] if source.is_file() else build_default(source_dir=source, **kwargs)
        for path in paths:
            print(path)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"load-clean: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
