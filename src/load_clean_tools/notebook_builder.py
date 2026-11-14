from __future__ import annotations

import io
import os
from pathlib import Path
import tempfile
import tokenize
from typing import Any

from load_clean.api import resolve_cell
from load_clean.parser import parse_load_clean_cell


def _dependency(name: str, extra: str = "tools") -> Any:
    try:
        return __import__(name)
    except ImportError as exc:
        raise RuntimeError(f"{name} is required; install load-clean[{extra}]") from exc


def is_autoremove_cell(source: str) -> bool:
    """Recognize the legacy marker only when it is an exact Python comment."""
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT and token.string.strip() == "#$<AUTOREMOVE>":
                return True
    except (tokenize.TokenError, IndentationError):
        pass
    return False


def resolve_cells(notebook: Any) -> Any:
    """Replace code cells containing load-clean magic with resolved source."""
    for index, cell in enumerate(notebook.cells, 1):
        if cell.cell_type != "code":
            continue
        try:
            first_line = cell.source.splitlines()[0:1]
            if first_line and first_line[0].strip().split(None, 1)[0:1] == ["%%load_clean_save"]:
                raise ValueError("Remove the save cell or tag it load-clean-remove before export")
            parsed = parse_load_clean_cell(cell.source)
            if parsed:
                cell.source = resolve_cell(parsed.import_line, parsed.names, parsed.mode)
        except Exception as exc:
            raise ValueError(f"Cell {index}: {exc}") from exc
    return notebook


def clean_notebook(notebook: Any) -> Any:
    """Remove marked cells, resolve magic, and clear execution state."""
    notebook.cells = [cell for cell in notebook.cells if not (
        "load-clean-remove" in cell.get("metadata", {}).get("tags", [])
        or (cell.cell_type == "code" and is_autoremove_cell(cell.source))
    )]
    resolve_cells(notebook)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    return notebook


def load_source_notebook(path: Path) -> Any:
    """Read the explicitly selected ipynb or py:percent source."""
    if path.suffix == ".ipynb":
        return _dependency("nbformat").read(path, as_version=4)
    if path.suffix == ".py":
        return _dependency("jupytext").read(path, fmt="py:percent")
    raise ValueError(f"Unsupported notebook source: {path}")


def find_notebook(source: Path) -> Path:
    """Return the explicitly selected notebook path."""
    return source


def _target(source: Path, output: str | Path, prefix: str) -> Path:
    return Path(output) / f"{source.stem.removeprefix(prefix)}.ipynb"


def _validate_paths(sources: list[Path], output: str | Path, prefix: str) -> None:
    targets: dict[Path, Path] = {}
    inputs = {source.resolve() for source in sources}
    for source in sources:
        target = _target(source, output, prefix).resolve()
        if target in inputs:
            raise ValueError(f"Output would overwrite an input notebook: {target}")
        if target in targets:
            raise ValueError(f"Output collision: {targets[target]} and {source} both map to {target}")
        targets[target] = source


def _execute(notebook: Any, source: Path) -> None:
    try:
        from nbclient import NotebookClient
    except ImportError as exc:
        raise RuntimeError("nbclient is required for --execute; install nbclient and an IPython kernel") from exc
    NotebookClient(notebook, resources={"metadata": {"path": str(source.parent.resolve())}}).execute()


def build(source: str | Path, *, output: str | Path = "build", prefix: str = "dev_", execute: bool = False, check: bool = False) -> Path:
    """Materialize one cleaned notebook, optionally executing or checking it."""
    if check and execute:
        raise ValueError("--execute cannot be combined with check")
    source_path = Path(source)
    _validate_paths([source_path], output, prefix)
    try:
        notebook = clean_notebook(load_source_notebook(source_path))
    except ValueError as exc:
        raise ValueError(f"{source_path}: {exc}") from exc
    if execute:
        _execute(notebook, source_path)
    target = _target(source_path, output, prefix)
    if check:
        return target
    nbformat = _dependency("nbformat")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, suffix=".ipynb", delete=False) as handle:
            temporary = Path(handle.name)
            nbformat.write(notebook, handle)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def build_default(*, source_dir: str | Path = "notebooks", output: str | Path = "build", prefix: str = "dev_", execute: bool = False, check: bool = False) -> list[Path]:
    """Build prefixed notebooks, rejecting ambiguous pairs and collisions."""
    if check and execute:
        raise ValueError("--execute cannot be combined with check")
    directory = Path(source_dir)
    sources = sorted(path for suffix in (".py", ".ipynb") for path in directory.glob(f"{prefix}*{suffix}"))
    if not sources:
        raise ValueError(f"No notebooks matching {prefix}*.py or {prefix}*.ipynb in {directory}")
    _validate_paths(sources, output, prefix)
    return [build(source, output=output, prefix=prefix, execute=execute, check=check) for source in sources]
