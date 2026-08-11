from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class LoadCleanCell:
    """
    Parsed %%load_clean cell.

    Args:
        mode:
            Resolution mode.
        import_line:
            Import statement.
        names:
            Requested symbols.
    """

    mode: str
    import_line: str
    names: list[str]
