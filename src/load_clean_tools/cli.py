from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import sys
from pathlib import Path

from .notebook_builder import CleanOptions, build, plan_build


def _options(parser: argparse.ArgumentParser) -> None:
    inputs = parser.add_argument_group('input selection')
    inputs.add_argument('paths', nargs='*', metavar='SOURCE', help='Notebook files/directories (default: notebooks)')
    inputs.add_argument('-s', '--source', action='append', help='Alternative to positional SOURCE; repeat for multiple inputs')
    inputs.add_argument('-r', '--recursive', action='store_true', help='Search directories recursively; preserve subdirectories in output')
    inputs.add_argument('--include', action='append', metavar='GLOB', help='Directory filename/relative-path glob; repeat (default: PREFIX*.ipynb and PREFIX*.py)')
    inputs.add_argument('--exclude', action='append', metavar='GLOB', help='Exclude matching directory-discovered paths; repeat')
    inputs.add_argument('--source-root', action='append', metavar='DIR', help='Exclusive static embedding lookup roots; repeat in priority order')
    outputs = parser.add_argument_group('output destinations')
    destination = outputs.add_mutually_exclusive_group()
    destination.add_argument('-o', '--output', '--output-dir', default='build', metavar='DIR', help='Output directory (default: build)')
    destination.add_argument('-O', '--output-file', metavar='FILE', help='Exact .ipynb output path; requires one explicit input file')
    outputs.add_argument('--prefix', default='dev_', help='Default discovery prefix; removed from output stems (default: dev_)')
    outputs.add_argument('--suffix', default='', help='Append to output stems before .ipynb')
    outputs.add_argument('--no-clobber', action='store_true', help='Refuse to overwrite existing generated outputs')
    outputs.add_argument('-n', '--dry-run', '--check', dest='check', action='store_true', help='Validate and report paths without writing or executing')
    cleaning = parser.add_argument_group('cleaning policies')
    cleaning.add_argument('--load-clean', choices=['resolve', 'strip', 'remove', 'keep'], default='resolve',
                          help='Resolve per mode; strip headers only; remove load-clean cells; or keep them (default: resolve)')
    cleaning.add_argument('--imports', choices=['keep', 'remove-cells'], default='keep', help='Keep imports or drop cells containing only imports (default: keep)')
    cleaning.add_argument('--outputs', choices=['clear', 'keep'], default='clear', help='Clear or retain existing outputs/counts before optional execution (default: clear)')
    tags = cleaning.add_mutually_exclusive_group()
    tags.add_argument('--remove-tag', action='append', metavar='TAG', help='Remove cells with this tag, in addition to load-clean-remove; repeat')
    tags.add_argument('--keep-tagged-cells', action='store_true', help='Disable removal by cell tags')
    cleaning.add_argument('--legacy-markers', action=argparse.BooleanOptionalAction, default=True, help='Honor exact legacy AUTOREMOVE comments (default: enabled)')
    cleaning.add_argument('--strip-setup', action='store_true', help='Remove standalone load_clean extension setup cells')
    cleaning.add_argument('--clear-metadata', action='store_true', help='Remove notebook/cell metadata, including kernelspec; use --kernel when executing')
    cleaning.add_argument('--drop-empty-cells', action='store_true', help='Remove cells with whitespace-only source')
    execution = parser.add_argument_group('execution (opt-in)')
    execution.add_argument('-x', '--execute', action='store_true', help='Execute exported notebook in a fresh kernel; incompatible with dry-run or keep policy')
    execution.add_argument('--kernel', help='Kernel name; defaults to notebook metadata or python3')
    execution.add_argument('--timeout', type=int, metavar='SECONDS', help='Per-cell timeout; -1 disables (default: no limit)')
    execution.add_argument('--execution-dir', metavar='DIR', help='Kernel working directory (default: source notebook directory)')
    execution.add_argument('--allow-errors', action='store_true', help='Continue through cell errors and save error outputs; requires --execute')
    reporting = parser.add_argument_group('reporting')
    verbosity = reporting.add_mutually_exclusive_group()
    verbosity.add_argument('-q', '--quiet', action='store_true', help='Suppress successful path/status output; errors remain on stderr')
    verbosity.add_argument('-v', '--verbose', action='store_true', help='Report selected policies and each input/output mapping on stderr')
    reporting.add_argument('-0', '--null', action='store_true', help='Terminate stdout paths with NUL instead of newline')


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build, check, pair, and synchronize notebooks.", allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "check"):
        command = commands.add_parser(name, help=f"{name.capitalize()} notebooks", allow_abbrev=False)
        _options(command)
    for name in ("pair", "sync"):
        command = commands.add_parser(name, help="Create a notebook/py:percent pair" if name == "pair" else "Synchronize a saved pair by file recency")
        command.add_argument("--source", required=True, help="One saved .ipynb or py:percent file (no directory scanning)")
    commands.add_parser("doctor", help="Report package version, installation paths and optional dependencies")
    return parser


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    if Path(sys.argv[0]).name == "load-clean-build":
        args_list.insert(0, "build")
    parser = create_parser()
    args = parser.parse_args(args_list)
    if args.command == "doctor":
        import load_clean

        try:
            version = importlib.metadata.version('load-clean')
        except importlib.metadata.PackageNotFoundError:
            version = 'unknown (distribution metadata unavailable; possibly a source checkout)'
        print(f'load-clean version: {version}')
        print(f'load_clean module: {Path(load_clean.__file__).resolve()}')
        print(f'load_clean_tools CLI: {Path(__file__).resolve()}')
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
            print("From a source checkout, run python -m pip install -e '.[notebook,tools]' ipykernel in this environment. No published distribution is assumed.")
        return 0
    try:
        if args.command in {"pair", "sync"}:
            from .sync import pair, sync

            for path, status in (pair if args.command == "pair" else sync)(args.source).items():
                print(f"{status}: {path}")
            return 0
        if args.source and args.paths:
            raise ValueError('Use positional SOURCE paths or --source, not both')
        sources = args.source or args.paths or ['notebooks']
        check = args.command == "check" or getattr(args, "check", False)
        options = CleanOptions(load_clean=args.load_clean, imports=args.imports, outputs=args.outputs,
                               remove_tags=() if args.keep_tagged_cells else ('load-clean-remove', *(args.remove_tag or [])),
                               legacy_markers=args.legacy_markers, strip_setup=args.strip_setup,
                               clear_metadata=args.clear_metadata, drop_empty_cells=args.drop_empty_cells)
        tasks = plan_build(sources, output=args.output, output_file=args.output_file, prefix=args.prefix,
                           suffix=args.suffix, recursive=args.recursive, include=args.include,
                           exclude=args.exclude, overwrite=not args.no_clobber)
        if args.verbose:
            print(f'Policies: load-clean={options.load_clean}, imports={options.imports}, outputs={options.outputs}; selected {len(tasks)} notebook(s)', file=sys.stderr)
        for source, target in tasks:
            path = build(source, output_file=target, execute=args.execute, check=check,
                         source_roots=args.source_root, clean_options=options, overwrite=not args.no_clobber,
                         timeout=args.timeout, kernel=args.kernel, execution_dir=args.execution_dir, allow_errors=args.allow_errors)
            if not args.quiet:
                print(path, end='\0' if args.null else '\n')
                if check:
                    print(f'Checked {source} -> {path}: static validation only; no code executed; no output written.', file=sys.stderr)
                else:
                    print(f'Built from {source} -> {path}', file=sys.stderr)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"load-clean: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
