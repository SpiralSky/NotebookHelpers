from __future__ import annotations

import ast

from .models import LoadCleanCell


VALID_MODES = {"default", "inline", "skeleton"}


def parse_line(line: str, cell: str) -> tuple[str, str]:
    """Parse magic arguments and the cell's import statement."""
    line = line.strip()
    mode = "default"
    import_line = ""
    if line:
        parts = line.split(None, 1)
        if parts[0] in VALID_MODES:
            mode = parts[0]
            import_line = parts[1] if len(parts) > 1 else ""
        else:
            import_line = line
    if not import_line and cell.splitlines():
        import_line = cell.splitlines()[0].strip()
    return mode, import_line


def parse_import(import_line: str) -> tuple[str, dict[str, str], bool, str]:
    """Parse an import into its module, targets, wildcard flag, and normalized form."""
    tree = ast.parse(import_line, mode="exec")
    if len(tree.body) != 1:
        raise ValueError(f"Unsupported import: {import_line}")
    node = tree.body[0]
    if isinstance(node, ast.Import) and len(node.names) == 1:
        module = node.names[0].name
        return module, {}, True, f"from {module} import *"
    if isinstance(node, ast.ImportFrom) and node.module:
        if any(alias.name == "*" for alias in node.names):
            return node.module, {}, True, import_line
        targets = {alias.name: alias.asname or alias.name for alias in node.names}
        return node.module, targets, False, import_line
    raise ValueError(f"Unsupported import: {import_line}")


def is_load_clean_cell(source: str) -> bool:
    """Return whether source begins with a %%load_clean magic line."""
    lines = source.splitlines()
    return bool(lines and lines[0].strip().startswith("%%load_clean"))


def parse_load_clean_cell(source: str) -> LoadCleanCell | None:
    """Parse a %%load_clean cell into the mode, import, and requested names."""
    if not is_load_clean_cell(source):
        return None
    lines = source.splitlines()
    parts = lines[0].strip().split(None, 1)
    mode = parts[1] if len(parts) == 2 else "default"
    import_line = next((line.strip() for line in lines[1:] if line.strip().startswith(("import ", "from "))), "")
    if not import_line:
        raise ValueError("%%load_clean cells require an import statement")
    try:
        tree = ast.parse("\n".join(lines[1:]))
    except SyntaxError as exc:
        raise ValueError("Invalid %%load_clean cell") from exc
    names = _requested_names(tree)
    if not names:
        _, targets, import_all, _ = parse_import(import_line)
        if not import_all:
            names = list(targets)
    return LoadCleanCell(mode, import_line, names)


def _requested_names(tree: ast.Module) -> list[str]:
    """Return names from the final top-level list expression, if present."""
    for node in reversed(tree.body):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.List):
            return [item.id for item in node.value.elts if isinstance(item, ast.Name)]
    return []
