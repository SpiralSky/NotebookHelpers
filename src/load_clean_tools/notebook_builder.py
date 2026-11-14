from __future__ import annotations

import io
import os
import shlex
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
        raise RuntimeError(f"{name} is required; install load-clean[{extra}] from a source checkout with python -m pip install -e '.[{extra}]'") from exc


def is_autoremove_cell(source: str) -> bool:
    """Recognize the legacy marker only when it is an exact Python comment."""
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT and token.string.strip() == "#$<AUTOREMOVE>":
                return True
    except (tokenize.TokenError, IndentationError):
        pass
    return False


def resolve_cells(notebook: Any, *, source_roots: list[str | Path] | None = None, cell_numbers: list[int] | None = None) -> Any:
    """Replace code cells containing load-clean magic with resolved source."""
    for index, cell in zip(cell_numbers or range(1, len(notebook.cells) + 1), notebook.cells):
        if cell.cell_type != "code":
            continue
        try:
            # IPython ignores leading blank lines before recognizing cell magics.
            first_line = cell.source.lstrip().splitlines()[0:1]
            if first_line and first_line[0].strip().split(None, 1)[0:1] == ["%%load_clean_save"]:
                raise ValueError("Remove the save cell or tag it load-clean-remove before export")
            parsed = parse_load_clean_cell(cell.source)
            if parsed:
                cell.source = resolve_cell(parsed.import_line, parsed.names, parsed.mode, source_roots=source_roots)
        except Exception as exc:
            raise ValueError(f"Cell {index}: {exc}. For unsupported embedding, keep an ordinary import in default mode and install the helper in the runtime environment.") from exc
    return notebook


def clean_notebook(notebook: Any, *, source_roots: list[str | Path] | None = None) -> Any:
    """Remove marked cells, resolve magic, and clear execution state."""
    retained = [(index, cell) for index, cell in enumerate(notebook.cells, 1) if not (
        "load-clean-remove" in cell.get("metadata", {}).get("tags", [])
        or (cell.cell_type == "code" and is_autoremove_cell(cell.source))
    )]
    notebook.cells = [cell for _, cell in retained]
    resolve_cells(notebook, source_roots=source_roots, cell_numbers=[index for index, _ in retained])
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
    raise ValueError(f"Unsupported notebook source: {path}; select .ipynb or py:percent")


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
            previous = targets[target]
            detail = ""
            if previous.with_suffix("") == source.with_suffix("") and {previous.suffix, source.suffix} == {".py", ".ipynb"}:
                choices = [shlex.join(["load-clean", "build", "--source", str(path), "--output", str(output), "--prefix", prefix]) for path in (previous, source)]
                detail = f"; paired source ambiguity. Select the intended saved input explicitly: {choices[0]} OR {choices[1]}. Build does not synchronize; reconcile copies or deliberately sync first."
            raise ValueError(f"Output collision: {previous} and {source} both map to {target}{detail}")
        targets[target] = source


def _execute(notebook: Any, source: Path) -> None:
    try:
        from nbclient import NotebookClient
    except ImportError as exc:
        raise RuntimeError("nbclient is required for --execute; install nbclient and an IPython kernel") from exc
    NotebookClient(notebook, resources={"metadata": {"path": str(source.parent.resolve())}}).execute()


def build(source: str | Path, *, output: str | Path = "build", prefix: str = "dev_", execute: bool = False, check: bool = False, source_roots: list[str | Path] | None = None) -> Path:
    """Materialize one cleaned notebook, optionally executing or checking it."""
    if check and execute:
        raise ValueError("--execute cannot be combined with check")
    source_path = Path(source)
    if not source_path.is_file():
        raise ValueError(f"Source does not exist or is not a file: {source_path}; select an existing saved .ipynb or py:percent file")
    if source_roots is not None:
        source_roots = [Path(root).resolve() for root in source_roots]
        for root in source_roots:
            if not root.is_dir():
                raise ValueError(f"Source root is not a directory: {root}; select the directory containing your helper modules")
    _validate_paths([source_path], output, prefix)
    try:
        notebook = clean_notebook(load_source_notebook(source_path), source_roots=source_roots)
    except (ValueError, RuntimeError, OSError, SyntaxError) as exc:
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


def build_default(*, source_dir: str | Path = "notebooks", output: str | Path = "build", prefix: str = "dev_", execute: bool = False, check: bool = False, source_roots: list[str | Path] | None = None) -> list[Path]:
    """Build prefixed notebooks, rejecting ambiguous pairs and collisions."""
    if check and execute:
        raise ValueError("--execute cannot be combined with check")
    directory = Path(source_dir)
    sources = sorted(path for suffix in (".py", ".ipynb") for path in directory.glob(f"{prefix}*{suffix}"))
    if not sources:
        raise ValueError(f"No notebooks matching {prefix}*.py or {prefix}*.ipynb in {directory}")
    _validate_paths(sources, output, prefix)
    return [build(source, output=output, prefix=prefix, execute=execute, check=check, source_roots=source_roots) for source in sources]
