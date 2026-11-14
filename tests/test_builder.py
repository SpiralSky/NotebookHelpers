from __future__ import annotations

import sys
from pathlib import Path

import pytest

from load_clean.parser import VALID_MODES, parse_load_clean_cell

try:
    import nbformat
except ImportError:
    nbformat = None

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


@pytest.mark.skipif(nbformat is None, reason="nbformat not installed")
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


@pytest.mark.skipif(nbformat is None, reason="nbformat not installed")
def test_clean_notebook_keeps_default_import() -> None:
    """Default mode retains its original import alongside expanded source."""
    notebook = nbformat.v4.new_notebook()
    notebook.cells = []
    assert clean_notebook(notebook).cells == []



class Cell(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class Notebook:
    def __init__(self, cells):
        self.cells = cells


def test_clean_removes_before_resolving_and_clears_outputs(monkeypatch):
    from load_clean_tools import notebook_builder as builder

    def resolve(*args):
        raise AssertionError("removed cell must not resolve")

    monkeypatch.setattr(builder, "resolve_cell", resolve)
    code = Cell(cell_type="code", source="x = 1", metadata={}, outputs=["old"], execution_count=2)
    markdown = Cell(cell_type="markdown", source="%%load_clean\nnot code", metadata={})
    removed = Cell(cell_type="code", source="%%load_clean\nfrom missing import x", metadata={"tags": ["load-clean-remove"]})
    result = builder.clean_notebook(Notebook([removed, markdown, code]))
    assert result.cells == [markdown, code]
    assert code.outputs == [] and code.execution_count is None


def test_legacy_marker_requires_exact_comment():
    from load_clean_tools.notebook_builder import is_autoremove_cell

    assert is_autoremove_cell("x = 1  #$<AUTOREMOVE>")
    assert not is_autoremove_cell('x = "#$<AUTOREMOVE>"')
    assert not is_autoremove_cell("# $<AUTOREMOVE> extra")
    assert not is_autoremove_cell("#$<AUTOREMOVE> extra")


def test_directory_pair_conflict_and_no_matches(tmp_path):
    from load_clean_tools.notebook_builder import build_default

    with pytest.raises(ValueError, match="No notebooks"):
        build_default(source_dir=tmp_path)
    (tmp_path / "dev_x.py").touch()
    (tmp_path / "dev_x.ipynb").touch()
    with pytest.raises(ValueError, match="collision"):
        build_default(source_dir=tmp_path)


def test_explicit_source_and_overwrite_protection(tmp_path, monkeypatch):
    from load_clean_tools import notebook_builder as builder

    source = tmp_path / "dev_x.py"
    source.touch()
    (tmp_path / "dev_x.ipynb").touch()
    seen = []
    monkeypatch.setattr(builder, "load_source_notebook", lambda path: seen.append(path) or Notebook([]))
    builder.build(source, output=tmp_path / "out", check=True)
    assert seen == [source]
    with pytest.raises(ValueError, match="overwrite"):
        builder.build(tmp_path / "dev_x.ipynb", output=tmp_path, prefix="")


def test_cli_reports_no_matches(tmp_path, capsys):
    from load_clean_tools.cli import main

    assert main(["check", "--source", str(tmp_path)]) == 1
    assert "No notebooks" in capsys.readouterr().err


def test_cli_check_alias_and_missing_source(tmp_path, capsys):
    from load_clean_tools.cli import main

    assert main(["build", "--source", str(tmp_path / "missing.ipynb")]) == 1
    assert "Source does not exist" in capsys.readouterr().err
    source = tmp_path / "dev_x.ipynb"
    source.touch()
    assert main(["build", "--source", str(source), "--check", "--execute"]) == 1
    assert "cannot be combined" in capsys.readouterr().err


def test_error_identifies_cell():
    from load_clean_tools.notebook_builder import clean_notebook

    notebook = Notebook([Cell(cell_type="code", source="%%load_clean\ninvalid", metadata={})])
    with pytest.raises(ValueError, match="Cell 1"):
        clean_notebook(notebook)


@pytest.mark.skipif(nbformat is None, reason="nbformat not installed")
def test_example_build_and_execute(tmp_path, monkeypatch):
    pytest.importorskip("nbclient")
    pytest.importorskip("ipykernel")
    examples = Path(__file__).resolve().parents[1] / "examples"
    monkeypatch.syspath_prepend(str(examples))
    target = build(examples / "dev_example.ipynb", output=tmp_path, execute=True)
    notebook = nbformat.read(target, as_version=4)
    assert "%%load_clean" not in notebook.cells[0].source
    assert notebook.cells[1].outputs[0].text.strip() == "Hello, world!"


def test_untagged_save_cell_requires_removal():
    notebook = Notebook([Cell(cell_type='code', source='%%load_clean_save helpers.py\nx = 1', metadata={})])
    with pytest.raises(ValueError, match='Cell 1: Remove the save cell or tag it load-clean-remove'):
        clean_notebook(notebook)


@pytest.mark.skipif(nbformat is None, reason='nbformat not installed')
def test_saved_module_export_journey(tmp_path, monkeypatch):
    from load_clean.api import save_cell

    monkeypatch.syspath_prepend(str(tmp_path))
    module = tmp_path / 'promoted_helpers.py'
    save_cell(module, 'def double(value):\n    return value * 2\n')
    notebook = nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_code_cell('%load_ext load_clean', metadata={'tags': ['load-clean-remove']}),
        nbformat.v4.new_code_cell('%%load_clean_save promoted_helpers.py\nraise RuntimeError("must not run")',
                                 metadata={'tags': ['load-clean-remove']}),
        nbformat.v4.new_code_cell('%%load_clean inline\nfrom promoted_helpers import double'),
        nbformat.v4.new_code_cell('assert double(4) == 8'),
    ])
    source = tmp_path / 'dev_promoted.ipynb'
    nbformat.write(notebook, source)
    original = source.read_bytes()
    before = module.read_bytes()
    destination = tmp_path / 'build'
    build(source, output=destination, check=True)
    assert not destination.exists()
    target = build(source, output=destination)
    result = nbformat.read(target, as_version=4)
    assert len(result.cells) == 2
    namespace = {}
    for cell in result.cells:
        assert '%%load_clean' not in cell.source
        assert cell.outputs == [] and cell.execution_count is None
        exec(cell.source, namespace)
    assert source.read_bytes() == original
    assert module.read_bytes() == before
    pytest.importorskip("nbclient")
    pytest.importorskip("ipykernel")
    executed = nbformat.read(build(source, output=destination, execute=True), as_version=4)
    assert all(cell.execution_count is not None for cell in executed.cells)
    assert source.read_bytes() == original
    assert module.read_bytes() == before


@pytest.mark.skipif(nbformat is None, reason="nbformat not installed")
def test_cli_feedback_explicit_roots_and_static_only(tmp_path, capsys):
    from load_clean_tools.cli import main

    helpers = tmp_path / "helpers"
    helpers.mkdir()
    (helpers / "uninstalled_p3.py").write_text('raise RuntimeError("must not import")\ndef value(): return 8\n')
    source = tmp_path / "dev_static.ipynb"
    nbformat.write(nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_code_cell('%%load_clean inline\nfrom uninstalled_p3 import value'),
        nbformat.v4.new_code_cell('raise RuntimeError("must not execute check")'),
    ]), source)
    original = source.read_bytes()
    output = tmp_path / "out"
    arguments = ["--source", str(source), "--output", str(output), "--source-root", str(helpers)]
    before = list(sys.path)
    assert main(["check", *arguments]) == 0
    captured = capsys.readouterr()
    target = output / "static.ipynb"
    assert captured.out == f"{target}\n"
    assert "no output written" in captured.err and "no code executed" in captured.err
    assert not output.exists() and source.read_bytes() == original
    assert "uninstalled_p3" not in sys.modules and sys.path == before
    assert main(["build", *arguments]) == 0
    captured = capsys.readouterr()
    assert captured.out == f"{target}\n"
    assert str(source) in captured.err and str(target) in captured.err
    assert source.read_bytes() == original


@pytest.mark.skipif(nbformat is None, reason="nbformat not installed")
def test_cli_source_cell_and_recovery(tmp_path, capsys):
    from load_clean_tools.cli import main

    source = tmp_path / "dev_bad.ipynb"
    nbformat.write(nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_code_cell('ignored', metadata={'tags': ['load-clean-remove']}),
        nbformat.v4.new_code_cell('%%load_clean inline\nimport impossible_helper'),
    ]), source)
    assert main(["check", "--source", str(source)]) == 1
    error = capsys.readouterr().err
    assert str(source) in error and "Cell 2" in error
    assert "from module import symbol" in error and "ordinary import" in error


def test_doctor_checkout_guidance(monkeypatch, capsys):
    from load_clean_tools import cli

    monkeypatch.setattr(cli.importlib.util, "find_spec", lambda name: None)
    assert cli.main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert "source checkout" in output and "python -m pip install -e" in output
