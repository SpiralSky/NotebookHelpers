"""Pure import-link syntax shared by notebook execution and static export.

Earlier argument-based layouts remain readable here; new cells use a source
reference comment. Parsing and formatting never resolve modules or access files.
"""
from __future__ import annotations

import ast
import re
import shlex

from .linked import fingerprint

_REFERENCE_PREFIX = '# Referenced Source: sha256:'
_REFERENCE_PATTERN = re.compile(re.escape(_REFERENCE_PREFIX) + r'([0-9a-f]{64})')


def import_node(statement: str) -> tuple[ast.Import | ast.ImportFrom, str]:
    tree = ast.parse(statement)
    if len(tree.body) != 1:
        raise ValueError('Use one import statement to identify the linked source')
    node = tree.body[0]
    if isinstance(node, ast.Import) and len(node.names) == 1:
        return node, node.names[0].name
    if isinstance(node, ast.ImportFrom) and node.module and not node.level:
        if any(item.name == '*' for item in node.names):
            raise ValueError('Use explicit names instead of a wildcard for editable links')
        if len({item.name for item in node.names}) != len(node.names):
            raise ValueError('Each linked name must occur only once')
        return node, node.module
    raise ValueError('Use import module or from module import name (absolute imports)')


def protected_import(statement: str) -> str:
    """Mark an identifying import as intentional for PyCharm/Flake8/Ruff."""
    node, _ = import_node(statement)
    return f'{ast.unparse(node)}  # noqa: F401'


def format_link_cell(statement: str, source: str) -> str:
    """Keep the import and persisted baseline on separate lines."""
    return (
        f'%%load_clean\n{protected_import(statement)}\n'
        f'{_REFERENCE_PREFIX}{fingerprint(source)}\n\n{source}'
    )


def parse_link_header(line: str) -> tuple[str, str, str] | None:
    args = shlex.split(line)
    if not args or args[0] != '--import':
        return None
    if (
        len(args) != 6 or args[2] != '--file' or args[4] != '--base'
        or not re.fullmatch('[0-9a-f]{64}', args[5])
    ):
        raise ValueError('Invalid generated import-link header; retain --import, --file and --base')
    import_node(args[1])
    return args[1], args[3], args[5]


def parse_link_cell(line: str, cell: str | None) -> tuple[str, str | None, str, str] | None:
    """Read comment-based links and earlier argument layouts without file access."""
    if line.strip() == '--include-imports':
        line = ''  # Sync always includes imports.
    legacy = parse_link_header(line)
    if legacy is not None:
        if cell is None:
            raise ValueError('Generated import links require a cell body')
        return (*legacy, cell)
    args = shlex.split(line)
    if args and args[0] != '--file':
        return None
    if args and (
        len(args) != 4 or args[2] != '--base'
        or not re.fullmatch('[0-9a-f]{64}', args[3])
    ):
        raise ValueError('Invalid generated import-link header; retain --file and --base')
    if cell is None:
        if not args:
            return None
        raise ValueError('Generated import links require a cell body')
    tree = ast.parse(cell)
    if not tree.body:
        raise ValueError('Keep the import statement below %%load_clean')
    node = tree.body[0]
    statement = ast.unparse(node)
    import_node(statement)
    lines = cell.splitlines(keepends=True)
    # The generated separator belongs to the link, not the editable source.
    if lines[node.end_lineno - 1].strip().endswith(';') or any(
        other.lineno == node.end_lineno for other in tree.body[1:]
    ):
        raise ValueError('Put the link import on its own line')
    remaining = lines[node.end_lineno:]
    if not args:
        reference = _REFERENCE_PATTERN.fullmatch(remaining[0].strip()) if remaining else None
        if reference is None:
            if len(tree.body) > 1 or any(
                text.strip().startswith('# Referenced Source:') for text in remaining
            ):
                raise ValueError(
                    'Keep the # Referenced Source: sha256:HASH comment immediately '
                    'below the import; preserve edits before reloading a link'
                )
            return None  # An initial import request, not yet an editable link.
        path, baseline = None, reference[1]
        remaining = remaining[1:]
    else:
        path, baseline = args[1], args[3]
    source = ''.join(remaining)
    if source.startswith('\r\n'):
        source = source[2:]
    elif source.startswith('\n'):
        source = source[1:]
    return statement, path, baseline, source
