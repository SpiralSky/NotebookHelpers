from __future__ import annotations

from pathlib import Path

import jupytext


def sync(path: str | Path = "notebooks", *, silent: bool = False, start_message: str | None = None) -> None:
    """Synchronize jupytext-paired Python notebooks in path."""
    if start_message and not silent:
        print(start_message)
    notebook_dir = Path(path)
    if not notebook_dir.exists():
        if not silent:
            print(f"Sync skipped: {notebook_dir} does not exist")
        return
    for py_file in notebook_dir.glob("*.py"):
        if not silent:
            print(f"Syncing {py_file}")
        jupytext.sync(py_file)
