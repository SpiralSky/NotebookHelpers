from __future__ import annotations

from pathlib import Path

import jupytext
import nbformat

from load_clean.api import resolve_cell
from load_clean.parser import parse_load_clean_cell


def is_autoremove_cell(source: str) -> bool:
    """Return whether source contains an AUTOREMOVE marker."""
    return "#$<AUTOREMOVE>" in source


def resolve_cells(notebook: nbformat.NotebookNode) -> nbformat.NotebookNode:
    """Replace each %%load_clean cell with source resolved by load_clean."""
    for cell in notebook.cells:
        parsed = parse_load_clean_cell(cell.source)
        if parsed:
            cell.source = resolve_cell(parsed.import_line, parsed.names, parsed.mode)
    return notebook


def clean_notebook(notebook: nbformat.NotebookNode) -> nbformat.NotebookNode:
    """Resolve load-clean cells and remove AUTOREMOVE cells."""
    resolve_cells(notebook)
    notebook.cells = [cell for cell in notebook.cells if not is_autoremove_cell(cell.source)]
    return notebook


def load_source_notebook(path: Path) -> nbformat.NotebookNode:
    """Read an ipynb or py:percent notebook."""
    if path.suffix == ".ipynb":
        return nbformat.read(path, as_version=4)
    return jupytext.read(path, fmt="py:percent")


def find_notebook(source: Path) -> Path:
    """Prefer the paired ipynb file when a py:percent path is supplied."""
    ipynb = source.with_suffix(".ipynb")
    return ipynb if source.suffix == ".py" and ipynb.exists() else source


def build(source: str | Path, *, output: str | Path = "build", prefix: str = "dev_") -> Path:
    """Materialize one cleaned notebook as an ipynb file."""
    source_path = find_notebook(Path(source))
    notebook = clean_notebook(load_source_notebook(source_path))
    name = source_path.stem.removeprefix(prefix)
    target_dir = Path(output)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{name}.ipynb"
    nbformat.write(notebook, target)
    return target


def build_default(*, source_dir: str | Path = "notebooks", output: str | Path = "build", prefix: str = "dev_") -> list[Path]:
    """Build every prefixed py:percent or ipynb notebook in source_dir."""
    directory = Path(source_dir)
    sources = sorted({find_notebook(path) for suffix in (".py", ".ipynb") for path in directory.glob(f"{prefix}*{suffix}")})
    return [build(source, output=output, prefix=prefix) for source in sources]
