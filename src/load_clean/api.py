from __future__ import annotations

from .resolver import LoadCleanResolver


def resolve_cell(
    import_line: str,
    names: list[str],
    mode: str = "default",
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

    Returns:
        Generated Python source.
    """
    return LoadCleanResolver().resolve(
        import_line,
        names,
        mode,
    )