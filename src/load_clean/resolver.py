from __future__ import annotations

import importlib.util
from pathlib import Path

from .parser import VALID_MODES, parse_import
from .slicer import SourceSlicer


def resolve_module(module: str) -> Path:
    """Resolve an importable module name to its source file."""
    spec = importlib.util.find_spec(module)
    if not spec or not spec.origin:
        raise ModuleNotFoundError(module)
    return Path(spec.origin)


class LoadCleanResolver:
    """Expand requested definitions from an import statement."""

    def resolve(self, import_line: str, names: list[str], mode: str = "default") -> str:
        """Resolve requested names into generated Python source."""
        if mode not in VALID_MODES:
            raise ValueError(f"Unknown mode {mode!r}. Expected {sorted(VALID_MODES)}")
        module, targets, import_all, _ = parse_import(import_line)
        selected = names or list(targets)
        slicer = SourceSlicer(resolve_module(module), {name: name for name in selected}, mode=mode, import_all=import_all and not selected)
        source = slicer.build().rstrip()
        if mode == "default":
            return f"{import_line}\n\n{source}" if source else import_line
        return source
