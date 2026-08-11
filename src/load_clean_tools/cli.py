from __future__ import annotations

import argparse

from .notebook_builder import build_default


def create_parser() -> argparse.ArgumentParser:
    """Create the load-clean-build argument parser."""
    parser = argparse.ArgumentParser(description="Build cleaned notebooks.")
    parser.add_argument("--source", default="notebooks")
    parser.add_argument("--output", default="build")
    parser.add_argument("--prefix", default="dev_")
    return parser


def main() -> None:
    """Run the notebook builder command."""
    args = create_parser().parse_args()
    build_default(source_dir=args.source, output=args.output, prefix=args.prefix)
