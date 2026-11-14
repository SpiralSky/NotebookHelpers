from __future__ import annotations

import os
from pathlib import Path

import pytest

from load_clean_tools.cli import main
from load_clean_tools.sync import pair, sync


def notebook(path):
    nbformat = pytest.importorskip("nbformat")
    pytest.importorskip("jupytext")
    nb = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(
        "print('kept')", execution_count=1,
        outputs=[nbformat.v4.new_output("stream", name="stdout", text="kept\n")]),
        nbformat.v4.new_code_cell("value = 1")])
    nbformat.write(nb, path)
    return nbformat


def newer(path, other):
    timestamp = max(path.stat().st_mtime, other.stat().st_mtime) + 2
    os.utime(path, (timestamp, timestamp))


def test_pair_and_sync_both_directions_preserve_outputs(tmp_path):
    source = tmp_path / "dev saved notebook.ipynb"
    nbformat = notebook(source)
    helper = tmp_path / "helpers.py"
    helper.write_text("ordinary = True\n")
    result = pair(source)
    text = source.with_suffix(".py")
    assert result == {source: "updated", text: "created"}
    assert "# %%" in text.read_text()
    sync(text)  # Jupytext may normalize metadata on the first round trip.
    assert sync(text) == {source: "unchanged", text: "unchanged"}
    text.write_text(text.read_text().replace("value = 1", "value = 2"))
    newer(text, source)
    result = sync(source)  # Selecting a path does not override the newest input.
    assert result[source] == "updated"
    nb = nbformat.read(source, as_version=4)
    assert nb.cells[1].source == "value = 2"
    assert nb.cells[0].outputs[0].text == "kept\n"
    nb.cells[1].source = "value = 3"
    nbformat.write(nb, source)
    newer(source, text)
    result = sync(text)
    assert result[text] == "updated"
    assert "value = 3" in text.read_text()
    assert nbformat.read(source, as_version=4).cells[0].outputs[0].text == "kept\n"
    assert helper.read_text() == "ordinary = True\n"


def test_pair_from_percent_and_restore_missing_counterpart(tmp_path):
    pytest.importorskip("jupytext")
    source = tmp_path / "dev notebook.py"
    source.write_text("# %%\nvalue = 1\n")
    result = pair(source)
    ipynb = source.with_suffix(".ipynb")
    assert result[ipynb] == "created"
    ipynb.unlink()
    assert sync(source)[ipynb] == "created"


def test_refuse_existing_counterpart_without_mutation(tmp_path):
    source = tmp_path / "dev.ipynb"
    notebook(source)
    text = source.with_suffix(".py")
    text.write_text("# %%\nvaluable = True\n")
    before = {p: p.read_bytes() for p in (source, text)}
    with pytest.raises(ValueError, match="Counterpart already exists"):
        pair(source)
    assert {p: p.read_bytes() for p in before} == before


def test_reject_unrecorded_and_unsupported_pair(tmp_path):
    source = tmp_path / "dev.ipynb"
    nbformat = notebook(source)
    with pytest.raises(ValueError, match="No supported pairing"):
        sync(source)
    nb = nbformat.read(source, as_version=4)
    nb.metadata["jupytext"] = {"formats": "ipynb,md"}
    nbformat.write(nb, source)
    before = source.read_bytes()
    with pytest.raises(ValueError, match="Unsupported pairing"):
        pair(source)
    assert source.read_bytes() == before


@pytest.mark.parametrize("action", [pair, sync])
def test_reject_directory_modules_and_extensions(tmp_path, action):
    pytest.importorskip("jupytext")
    with pytest.raises(ValueError, match="not a directory"):
        action(tmp_path)
    module = tmp_path / "helpers.py"
    module.write_text("value = 1\n")
    with pytest.raises(ValueError, match="ordinary helper modules"):
        action(module)
    unsupported = tmp_path / "notes.md"
    unsupported.write_text("# Notes\n")
    with pytest.raises(ValueError, match="Unsupported notebook source"):
        action(unsupported)
    assert not module.with_suffix(".ipynb").exists()


def test_missing_optional_dependency(tmp_path, monkeypatch, capsys):
    import builtins
    original = builtins.__import__

    def missing(name, *args, **kwargs):
        if name == "jupytext":
            raise ImportError("not installed")
        return original(name, *args, **kwargs)

    source = tmp_path / "dev.ipynb"
    source.write_text("{}")
    monkeypatch.setattr(builtins, "__import__", missing)
    assert main(["pair", "--source", str(source)]) == 1
    assert "jupytext is required; install load-clean[tools]" in capsys.readouterr().err
    assert not source.with_suffix(".py").exists()


def test_cli_reports_exact_paths_and_help(tmp_path, capsys):
    source = tmp_path / "dev saved.ipynb"
    notebook(source)
    assert main(["pair", "--source", str(source)]) == 0
    assert capsys.readouterr().out.splitlines() == [f"updated: {source}", f"created: {source.with_suffix('.py')}"]
    before = {path: path.read_bytes() for path in (source, source.with_suffix(".py"))}
    assert main(["sync", "--source", str(source)]) == 0
    expected = [f"{'unchanged' if path.read_bytes() == content else 'updated'}: {path}" for path, content in before.items()]
    assert capsys.readouterr().out.splitlines() == expected
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "pair" in capsys.readouterr().out


def test_directory_ambiguity_offers_valid_choices_without_writes(tmp_path, capsys):
    import shlex

    source = tmp_path / "dev_saved notebook.ipynb"
    notebook(source)
    pair(source)
    paths = [source, source.with_suffix(".py")]
    before = {p: p.read_bytes() for p in paths}
    output = tmp_path / "build output"
    assert main(["build", "--source", str(tmp_path), "--output", str(output)]) == 1
    error = capsys.readouterr().err
    assert "paired source ambiguity" in error
    for path in paths:
        assert shlex.join(["load-clean", "build", "--source", str(path), "--output", str(output), "--prefix", "dev_"]) in error
        assert main(["check", "--source", str(path), "--output", str(output)]) == 0
    assert not output.exists()
    assert {p: p.read_bytes() for p in paths} == before


def test_divergent_saved_inputs_follow_recency_without_merging(tmp_path):
    source = tmp_path / "dev_conflict.ipynb"
    nbformat = notebook(source)
    pair(source)
    text = source.with_suffix(".py")
    nb = nbformat.read(source, as_version=4)
    nb.cells[1].source = "notebook_only = 2"
    nbformat.write(nb, source)
    text.write_text(text.read_text().replace("value = 1", "text_only = 3"))
    newer(text, source)
    sync(source)
    result = nbformat.read(source, as_version=4)
    assert result.cells[1].source == "text_only = 3"
    assert "notebook_only" not in text.read_text()


def test_sync_refuses_unrelated_counterpart(tmp_path):
    source = tmp_path / "dev.ipynb"
    notebook(source)
    pair(source)
    text = source.with_suffix(".py")
    text.write_text("# %%\nunrelated = True\n")
    before = {p: p.read_bytes() for p in (source, text)}
    with pytest.raises(ValueError, match="no matching pairing"):
        sync(source)
    assert {p: p.read_bytes() for p in before} == before


def test_genuine_collision_is_not_reported_as_pair(tmp_path):
    from load_clean_tools.notebook_builder import _validate_paths

    sources = [tmp_path / "dev_x.py", tmp_path / "x.py"]
    with pytest.raises(ValueError, match="Output collision") as exc:
        _validate_paths(sources, tmp_path / "out", "dev_")
    assert "paired source ambiguity" not in str(exc.value)
    assert not (tmp_path / "out").exists()
