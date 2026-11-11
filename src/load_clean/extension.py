from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from IPython.core.error import UsageError
from IPython.core.magic import Magics, cell_magic, line_magic, magics_class

from .api import resolve_cell
from .parser import parse_import, parse_load_clean_cell
from .resolver import resolve_module


def _fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@magics_class
class LoadCleanMagics(Magics):
    """Load definitions into this shell and inspect their source."""

    def __init__(self, shell: Any) -> None:
        super().__init__(shell)
        self.sources: dict[str, tuple[Path, str]] = {}

    @staticmethod
    def _parse(line: str, cell: str = ""):
        try:
            parsed = parse_load_clean_cell(f"%%load_clean {line}\n{cell}")
            if parsed is None:
                raise ValueError("Expected a %%load_clean cell")
            return parsed
        except (ValueError, SyntaxError) as exc:
            raise UsageError(str(exc)) from exc

    @staticmethod
    def _source(parsed):
        try:
            module, _, _, _ = parse_import(parsed.import_line)
            path = resolve_module(module)
            source = resolve_cell(parsed.import_line, parsed.names, parsed.mode)
            return module, path, source
        except (ValueError, SyntaxError, ImportError, OSError) as exc:
            raise UsageError(str(exc)) from exc

    @cell_magic
    def load_clean(self, line: str, cell: str = "") -> None:
        """Execute the import or selected static definitions in the user namespace."""
        parsed = self._parse(line, cell)
        if parsed.mode == "default":
            # Execute exactly the user's import, with normal Python binding semantics.
            exec(parsed.import_line, self.shell.user_ns)
            try:
                module, _, _, _ = parse_import(parsed.import_line)
                path = resolve_module(module)
                self.sources[module] = (path, _fingerprint(path))
            except (ValueError, SyntaxError, ImportError, OSError):
                # Normal imports may have no inspectable Python source.
                pass
            return
        module, path, source = self._source(parsed)
        if not source.strip():
            raise UsageError(f"No definitions found in {module}")
        exec(compile(source, str(path), "exec"), self.shell.user_ns)
        self.sources[module] = (path, _fingerprint(path))

    @line_magic
    def load_clean_preview(self, line: str) -> None:
        """Print the source that a load_clean request would generate."""
        parsed = self._parse(line)
        _, _, source = self._source(parsed)
        print(source)

    @line_magic
    def load_clean_status(self, line: str) -> None:
        """Show recorded source fingerprints and whether files have changed."""
        if line.strip():
            raise UsageError("%load_clean_status takes no arguments")
        if not self.sources:
            print("No load_clean sources recorded")
            return
        for module, (path, fingerprint) in sorted(self.sources.items()):
            try:
                current = _fingerprint(path)
                state = "unchanged" if current == fingerprint else "changed"
            except OSError:
                state = "unavailable"
            print(f"{module}: {state} sha256:{fingerprint} ({path})")

    @line_magic
    def load_clean_check(self, line: str) -> None:
        """Validate a load request without executing it."""
        if not line.strip():
            self.load_clean_status("")
            return
        parsed = self._parse(line)
        module, path, source = self._source(parsed)
        try:
            compile(source, str(path), "exec")
        except SyntaxError as exc:
            raise UsageError(str(exc)) from exc
        print(f"{module}: valid sha256:{_fingerprint(path)}")

    @line_magic
    def load_clean_materialize(self, line: str) -> None:
        """Put generated ordinary Python in a new input cell."""
        parsed = self._parse(line)
        _, _, source = self._source(parsed)
        self.shell.set_next_input(source, replace=False)


def load_ipython_extension(ipython: Any) -> None:
    ipython.register_magics(LoadCleanMagics)
