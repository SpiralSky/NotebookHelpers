from __future__ import annotations

from pathlib import Path

from .resolver import LoadCleanResolver
from .save import SaveResult, save_cell


def resolve_cell(
    import_line: str,
    names: list[str],
    mode: str = "default",
    *,
    source_roots: list[str | Path] | None = None,
    include_imports: bool | None = None,
) -> str:
    """
    Resolve a load_clean import into source.

    Args:
        import_line:
            Import statement.

        names:
            Requested symbols.

        mode:
            Resolution mode.

        include_imports:
            Retain dependency imports. Defaults to false for copy/skeleton,
            true for legacy inline. Does not control linked synchronization.

        source_roots:
            Exclusive ordered filesystem roots for embedding; defaults to sys.path.

    Returns:
        Generated Python source.
    """
    return LoadCleanResolver().resolve(
        import_line,
        names,
        mode,
        source_roots=source_roots,
        include_imports=include_imports,
    )
