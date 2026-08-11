from __future__ import annotations

from load_clean.api import resolve_cell


def test_resolve_cell_uses_existing_slicer() -> None:
    """Extract only the requested definition from a source module."""
    source = resolve_cell("from load_clean.renderer import render_array", ["render_array"], "inline")
    assert source.startswith("def render_array(")


def test_default_resolution_keeps_import_line() -> None:
    """Preserve the original import before the generated definition."""
    import_line = "from load_clean.renderer import render_array"
    source = resolve_cell(import_line, ["render_array"])
    assert source.startswith(f"{import_line}\n\ndef render_array(")


def test_skeleton_resolution_replaces_function_body() -> None:
    """Use SourceSlicer's skeleton mode without duplicating extraction logic."""
    source = resolve_cell("from load_clean.renderer import render_array", ["render_array"], "skeleton")
    assert "pass" in source
    assert 'return "[]\\n"' not in source
