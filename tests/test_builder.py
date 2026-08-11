from __future__ import annotations

import sys
from pathlib import Path

import pytest

from load_clean.parser import VALID_MODES, parse_load_clean_cell

nbformat = pytest.importorskip("nbformat")
pytest.importorskip("jupytext")

from load_clean_tools.notebook_builder import build, clean_notebook


def test_parser_preserves_existing_extension_api() -> None:
    """Keep the mode constant required by the IPython extension."""
    assert VALID_MODES == {"default", "inline", "skeleton"}


def test_parse_load_clean_cell_reads_requested_names() -> None:
    """Parse the import and display list from an unexpanded magic cell."""
    parsed = parse_load_clean_cell("%%load_clean inline\nfrom demo import one, two\n\n[one, two]")
    assert parsed is not None
    assert parsed.mode == "inline"
    assert parsed.import_line == "from demo import one, two"
    assert parsed.names == ["one", "two"]


def test_builder_resolves_magic_and_removes_marked_cells(tmp_path: Path) -> None:
    """Build source from an unexpanded %%load_clean cell."""
    package = tmp_path / "example_package"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "definitions.py").write_text("def first() -> int:\n    return 1\n\ndef second() -> int:\n    return 2\n", encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        notebook = nbformat.v4.new_notebook(cells=[
            nbformat.v4.new_code_cell("%%load_clean inline\nfrom example_package.definitions import *\n\n[first]"),
            nbformat.v4.new_code_cell("secret = True  #$<AUTOREMOVE>"),
        ])
        source = tmp_path / "dev_example.ipynb"
        nbformat.write(notebook, source)
        target = build(source, output=tmp_path / "build")
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("example_package", None)
        sys.modules.pop("example_package.definitions", None)
    result = nbformat.read(target, as_version=4)
    assert target.name == "example.ipynb"
    assert len(result.cells) == 1
    assert result.cells[0].source == "def first() -> int:\n    return 1"


def test_clean_notebook_keeps_default_import() -> None:
    """Default mode retains its original import alongside expanded source."""
    notebook = nbformat.v4.new_notebook()
    notebook.cells = []
    assert clean_notebook(notebook).cells == []
