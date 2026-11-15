from __future__ import annotations

import hashlib
import shlex
from pathlib import Path
from typing import Any

from IPython.core.error import UsageError
from IPython.core.magic import Magics, cell_magic, line_cell_magic, line_magic, magics_class

from .api import resolve_cell, save_cell
from .parser import parse_import, parse_load_clean_cell
from .resolver import resolve_module
from .linked import load_link, parse_header, sync_link
from ._import_link_format import parse_link_cell
from .import_link import synchronize, execute as execute_import_link


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

    @line_cell_magic
    def load_clean(self, line: str, cell: str | None = None) -> None:
        """Load a linked file, or synchronize and execute its editable cell."""
        imported = None
        try:
            import_header = parse_link_cell(line, cell)
            if import_header is not None:
                statement, path, baseline, source = import_header
                imported = synchronize(statement, source, baseline, path)
            elif cell is not None and not line.strip():
                imported = synchronize(cell)
            if imported is not None:
                self.shell.set_next_input(imported.cell, replace=True)
        except (ValueError, SyntaxError, OSError) as exc:
            raise UsageError(str(exc)) from exc
        if imported is not None:
            execute_import_link(imported, self.shell.user_ns)
            return
        try:
            linked = parse_header(line)
            if cell is None:
                if linked is None or linked[1] is not None:
                    raise ValueError('Usage: %load_clean path.py (load without execution)')
                result = load_link(linked[0])
                self.shell.set_next_input(result.cell, replace=False)
                return
            if linked is not None:
                result = sync_link(linked[0], cell, linked[1])
                self.shell.set_next_input(result.cell, replace=True)
        except (ValueError, SyntaxError, OSError) as exc:
            raise UsageError(str(exc)) from exc
        if linked is not None:
            # Runtime errors occur after synchronization and must not undo the save.
            exec(compile(result.source, str(result.path), 'exec', dont_inherit=True), self.shell.user_ns)
            return

        # Keep the original import-selection forms as explicit compatibility paths.
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

    @cell_magic
    def load_clean_save(self, line: str, cell: str = "") -> None:
        """Preview or create a whole-cell module, without executing its body."""
        try:
            arguments = shlex.split(line)
            preview = bool(arguments and arguments[0] == "--preview")
            if preview:
                arguments.pop(0)
            if len(arguments) != 1 or arguments[0].startswith("-"):
                raise ValueError("Usage: %%load_clean_save [--preview] path.py")
            result = save_cell(arguments[0], cell, preview=preview)
        except (ValueError, SyntaxError, OSError) as exc:
            raise UsageError(str(exc)) from exc
        if preview:
            print(f"Preview destination: {result.path}\nExact source follows:")
            print(result.source, end="")
            return
        print(f"Wrote {result.path}")
        if result.import_line:
            print(f"Replace this writer cell with: {result.import_line}")
        else:
            print("Configure the project source path (for example, pip install -e .) "
                  "before importing this module; no import was run.")
        print("The module now owns this code. Add a test; remove this writer cell "
              "or tag it load-clean-remove before export.")

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

        print("Status compares on-disk source with the last load; it cannot certify downstream results are fresh. "
              "Reload ordinary modules or rerun inline cells, then rerun dependent cells.")

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
        print(f"{module}: valid sha256:{_fingerprint(path)}; static check only, no code executed or output written")

    @line_magic
    def load_clean_materialize(self, line: str) -> None:
        """Put generated ordinary Python in a new input cell."""
        parsed = self._parse(line)
        _, _, source = self._source(parsed)
        self.shell.set_next_input(source, replace=False)


def load_ipython_extension(ipython: Any) -> None:
    ipython.register_magics(LoadCleanMagics)
