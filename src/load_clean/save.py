"""Whole-cell promotion without importing or executing the saved program."""
from __future__ import annotations

import codecs
from dataclasses import dataclass
from importlib.machinery import PathFinder
import io
import keyword
import os
from pathlib import Path
import sys
import tempfile
import tokenize


@dataclass(frozen=True)
class SaveResult:
    path: Path
    source: str
    import_line: str | None


def _import_line(path: Path) -> str | None:
    """Check ordinary filesystem imports without running package initializers."""
    for root in sys.path:
        try:
            relative = path.relative_to(Path(root or '.').resolve()).with_suffix('')
        except ValueError:
            continue
        parts = list(relative.parts)
        if parts[-1] == '__init__':
            parts.pop()
        if not parts or any(not part.isidentifier() or keyword.iskeyword(part) for part in parts):
            continue
        locations = None
        spec = None
        for index in range(len(parts)):
            spec = PathFinder.find_spec('.'.join(parts[:index + 1]), locations)
            if spec is None:
                break
            if index < len(parts) - 1:
                locations = spec.submodule_search_locations
                if locations is None:
                    spec = None
                    break
        if spec and spec.origin and Path(spec.origin).resolve() == path:
            return f"import {'.'.join(parts)}"
    return None


def save_cell(destination: str | Path, source: str, *, preview: bool = False) -> SaveResult:
    """Validate exact UTF-8 source, then preview or atomically create a module.

    Parents must exist. Symlink components and existing destinations are refused;
    replacement is deliberately unsupported. Filesystem parents must remain
    trusted and stable during this operation.
    """
    path = Path(destination).expanduser().absolute()
    if path.suffix != '.py':
        raise ValueError('Destination must have a .py suffix')
    if any(component.is_symlink() for component in (path, *path.parents)):
        raise ValueError('Symlink destinations and parent directories are not supported')
    path = path.resolve()
    if not path.parent.is_dir():
        raise ValueError(f'Parent directory must already exist: {path.parent}')
    if path.exists() and not path.is_file():
        raise ValueError(f'Destination is not a regular file: {path}')
    data = source.encode('utf-8')
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    if codecs.lookup(encoding).name not in {'utf-8', 'utf-8-sig'}:
        raise ValueError('Source encoding declaration must be UTF-8')
    compile(data, str(path), 'exec', dont_inherit=True)
    if not preview and path.exists():
        raise FileExistsError(f'Destination already exists: {path}; edit the module instead')
    result = SaveResult(path, source, _import_line(path))
    if preview:
        return result
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.load-clean-', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        # A hard link publishes the complete file, refusing even a racing writer.
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return SaveResult(path, source, _import_line(path))
