from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from .notebook_builder import _dependency


_FORMATS = "ipynb,py:percent"


def _inputs(path: str | Path):
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"Select one existing notebook file, not a directory: {source}")
    if source.suffix not in {".ipynb", ".py"}:
        raise ValueError(f"Unsupported notebook source: {source}; use .ipynb or py:percent")
    jupytext = _dependency("jupytext")
    if source.suffix == ".py" and jupytext.guess_format(source.read_text(encoding="utf-8"), ext=".py")[0] != "percent":
        raise ValueError(f"Not a py:percent notebook: {source}; ordinary helper modules cannot be paired")
    notebook = jupytext.read(source, fmt="ipynb" if source.suffix == ".ipynb" else "py:percent")
    formats = notebook.metadata.get("jupytext", {}).get("formats")
    if formats is not None and formats != _FORMATS:
        raise ValueError(f"Unsupported pairing formats in {source}: {formats!r}; expected {_FORMATS}")
    return source, notebook


def _run(source: Path, *, pair: bool) -> dict[Path, str]:
    # Use the supported CLI in this interpreter; paths never enter a shell.
    paths = [source.with_suffix(".ipynb"), source.with_suffix(".py")]
    before = {path: path.read_bytes() if path.exists() else None for path in paths}
    args = ["--quiet", "--set-formats", _FORMATS] if pair else ["--quiet", "--sync"]
    try:
        subprocess.run([sys.executable, "-m", "jupytext", *args, "--", str(source)], check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Jupytext could not synchronize the pair (exit {exc.returncode}); inspect its diagnostic and reconcile saved copies before retrying") from exc
    return {path: "created" if before[path] is None else "unchanged" if path.read_bytes() == before[path] else "updated" for path in paths}


def pair(path: str | Path) -> dict[Path, str]:
    """Create a same-directory ipynb/py:percent pair from one saved file."""
    source, _ = _inputs(path)
    counterpart = source.with_suffix(".py" if source.suffix == ".ipynb" else ".ipynb")
    if counterpart.exists():
        raise ValueError(f"Counterpart already exists: {counterpart}; use sync for a recorded pair, or back up and reconcile both copies first")
    return _run(source, pair=True)


def sync(path: str | Path) -> dict[Path, str]:
    """Sync one recorded pair by Jupytext recency rules, preserving notebook outputs."""
    source, notebook = _inputs(path)
    if notebook.metadata.get("jupytext", {}).get("formats") != _FORMATS:
        raise ValueError(f"No supported pairing recorded in {source}; run load-clean pair --source {str(source)!r} first")
    counterpart = source.with_suffix(".py" if source.suffix == ".ipynb" else ".ipynb")
    if counterpart.exists():
        _, other = _inputs(counterpart)
        if other.metadata.get("jupytext", {}).get("formats") != _FORMATS:
            raise ValueError(f"Counterpart has no matching pairing: {counterpart}; back up and reconcile both copies first")
    return _run(source, pair=False)
