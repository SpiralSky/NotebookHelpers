"""Whole-file synchronization with a baseline carried in the notebook cell."""
from __future__ import annotations

import codecs
from dataclasses import dataclass
import difflib
import hashlib
import io
import os
from pathlib import Path
import re
import shlex
import stat
import tempfile
import tokenize

from .save import save_cell


def canonical(source: str) -> str:
    # Notebook frontends can add/remove the final newline; it is not an edit.
    return source.removeprefix('\ufeff').replace('\r\n', '\n').replace('\r', '\n').rstrip('\n') + '\n'


def fingerprint(source: str) -> str:
    return hashlib.sha256(canonical(source).encode('utf-8')).hexdigest()


def validate(source: str, filename: str = '<linked cell>') -> str:
    source = canonical(source)
    data = source.encode('utf-8')
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    if codecs.lookup(encoding).name not in {'utf-8', 'utf-8-sig'}:
        raise ValueError('Linked source must use UTF-8')
    compile(data, filename, 'exec', dont_inherit=True)
    return source


def destination(value: str | Path) -> Path:
    path = Path(value).expanduser().absolute()
    if path.suffix != '.py':
        raise ValueError('A linked cell requires a .py file path')
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('Symlink files and parent directories are not supported')
    if not path.parent.is_dir():
        raise ValueError(f'Parent directory must already exist: {path.parent}')
    if path.exists() and not path.is_file():
        raise ValueError(f'Not a regular file: {path}')
    return path.resolve()


def parse_header(line: str) -> tuple[str, str | None] | None:
    """Distinguish the new path interface from legacy import-selection modes."""
    args = shlex.split(line)
    if not args or args[0] in {'default', 'inline', 'skeleton', 'from', 'import'}:
        return None
    if len(args) not in (1, 3) or (len(args) == 3 and (
        args[1] != '--base' or not re.fullmatch('[0-9a-f]{64}', args[2])
    )):
        raise ValueError('Usage: %%load_clean path.py [--base SHA256]')
    if not args[0].endswith('.py'):
        raise ValueError('A linked cell requires a .py file path')
    return args[0], args[2] if len(args) == 3 else None


@dataclass(frozen=True)
class LinkedSource:
    path: Path
    source: str
    status: str

    @property
    def cell(self) -> str:
        return f'%%load_clean {shlex.quote(str(self.path))} --base {fingerprint(self.source)}\n{self.source}'


def load_link(value: str | Path) -> LinkedSource:
    path = destination(value)
    source = validate(path.read_bytes().decode('utf-8'), str(path))
    return LinkedSource(path, source, 'Loaded from file')


def _replace(path: Path, before: bytes, source: str) -> None:
    """Atomic publication with an optimistic last-moment conflict check.

    Ordinary editors do not share a lock with us. A concurrent external writer
    after the final check remains possible; this is not a filesystem CAS.
    """
    mode = stat.S_IMODE(path.stat().st_mode)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.load-clean-', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(source.encode('utf-8'))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        destination(path)
        if path.read_bytes() != before:
            raise ValueError('Source changed during synchronization; nothing applied. Run again to review.')
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def sync_link(value: str | Path, source: str, baseline: str | None = None) -> LinkedSource:
    path = destination(value)
    local = canonical(source)
    if not path.exists():
        if baseline is not None:
            raise ValueError(f'Linked source was deleted: {path}; restore it or deliberately create a new link')
        local = validate(local, str(path))
        save_cell(path, local)
        return LinkedSource(path, local, 'Created file')

    before = path.read_bytes()
    remote = canonical(before.decode('utf-8'))
    local_hash, remote_hash = fingerprint(local), fingerprint(remote)
    if local_hash == remote_hash:
        return LinkedSource(path, validate(local, str(path)), 'In sync')
    if baseline is None:
        raise ValueError(f'Existing file differs and this cell has no baseline. Load it with %load_clean {shlex.quote(str(path))}; preserve your cell edits before reconciling.')
    if local_hash == baseline:
        return LinkedSource(path, validate(remote, str(path)), 'Updated from file')
    if remote_hash == baseline:
        local = validate(local, str(path))
        _replace(path, before, local)
        return LinkedSource(path, local, 'Saved to file')
    diff = ''.join(difflib.unified_diff(remote.splitlines(True), local.splitlines(True),
                                        fromfile=str(path), tofile='notebook cell'))
    raise ValueError('Sync conflict: both cell and file changed. Nothing written or executed. '
                     'Reconcile both copies (or make their contents identical), then run again.\n' + diff)
