"""Import-addressed links, preserving unselected module source."""
from __future__ import annotations

import ast
from dataclasses import dataclass
import difflib
import importlib
from importlib.machinery import PathFinder
import importlib.util
from pathlib import Path
import sys

from .linked import canonical, destination, fingerprint, sync_link, validate, _replace
# Keep earlier imports of these syntax helpers compatible.
from ._import_link_format import (
    format_link_cell,
    import_node,
    parse_link_header as parse_link_header,
    parse_link_cell as parse_link_cell,
)


def module_path(name: str) -> Path:
    """Use ordinary filesystem import precedence without running initializers."""
    importlib.invalidate_caches()
    locations = None
    parts = name.split('.')
    for index in range(len(parts)):
        fullname = '.'.join(parts[:index + 1])
        spec = PathFinder.find_spec(fullname, locations)
        if spec is None:
            raise ValueError(f'No filesystem Python module found for {fullname}; install the project in the kernel environment')
        cached = sys.modules.get(fullname)
        if cached is not None:
            cached_spec = getattr(cached, '__spec__', None)
            if cached_spec is None or cached_spec.origin != spec.origin:
                raise ValueError(f'Cached module {fullname} has a different source; restart the kernel')
        if index < len(parts) - 1:
            locations = spec.submodule_search_locations
            if locations is None:
                raise ValueError(f'{fullname} is not a package')
    if not spec.origin or not spec.origin.endswith('.py'):
        raise ValueError(f'{name} has no editable Python source')
    return destination(spec.origin)


def _definition_name(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        return node.targets[0].id
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
        return node.target.id
    return None


def spans(source: str, names: list[str]) -> list[tuple[int, int, str]]:
    tree = ast.parse(source)
    # Reject any additional binding of a requested name, including assignments
    # inside conditionals. They make selecting a single source definition unsafe.
    for name in names:
        bindings = []
        def visit(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name == name:
                    bindings.append(node)
                return
            if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)) and node.id == name:
                bindings.append(node)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if (alias.asname or (alias.name.split('.')[0] if isinstance(node, ast.Import) else alias.name)) == name:
                        bindings.append(node)
                    if alias.name == '*':
                        bindings.append(node)
            for child in ast.iter_child_nodes(node):
                visit(child)
        for node in tree.body:
            visit(node)
        if len(bindings) != 1:
            raise ValueError(f'{name}: missing or ambiguous definition; link the whole module instead')
    selected = [node for node in tree.body if _definition_name(node) in names]
    if len(selected) != len(names):
        raise ValueError('Selected names must be directly defined top-level functions, classes, or simple assignments; re-exports are not editable links')
    result = []
    for node in selected:
        start = min([node.lineno, *(d.lineno for d in getattr(node, 'decorator_list', []))]) - 1
        end = node.end_lineno
        if any(other is not node and other.lineno <= end and other.end_lineno >= start + 1 for other in tree.body):
            raise ValueError('Definitions sharing a line cannot be linked separately')
        result.append((start, end, _definition_name(node)))
    return result


def import_spans(source: str) -> list[tuple[int, int, str]]:
    tree = ast.parse(source)
    result = []
    for index, node in enumerate(tree.body):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if any(other is not node and other.lineno <= node.end_lineno
               and other.end_lineno >= node.lineno for other in tree.body):
            raise ValueError('Imports sharing a line cannot be linked separately')
        result.append((node.lineno - 1, node.end_lineno, f'import:{index}'))
    return result


def selection(source: str, names: list[str], *, include_imports: bool = True) -> str:
    lines = source.splitlines(keepends=True)
    regions = spans(source, names)
    if include_imports:
        regions += import_spans(source)
    return canonical('\n\n'.join(''.join(lines[start:end]).rstrip('\r\n')
                                 for start, end, _ in sorted(regions)))


def replace_selection(remote: str, local: str, names: list[str]) -> str:
    validate(local)
    local_tree = ast.parse(local)
    definitions = [node for node in local_tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))]
    if len(definitions) != len(names) or {_definition_name(node) for node in definitions} != set(names):
        raise ValueError('Keep exactly the selected definitions and their original names')
    local_lines = local.splitlines(keepends=True)
    local_regions = spans(local, names) + import_spans(local)
    owned = {line for start, end, _ in local_regions for line in range(start, end)}
    if any(text.strip() for index, text in enumerate(local_lines) if index not in owned):
        raise ValueError('Place comments inside the selected definitions; extra cell content cannot be saved to a selected region')
    replacements = {name: ''.join(local_lines[start:end]).rstrip('\r\n') + '\n'
                    for start, end, name in spans(local, names)}
    lines = remote.splitlines(keepends=True)
    edits = [(start, end, replacements[name]) for start, end, name in spans(remote, names)]
    remote_imports = import_spans(remote)
    local_imports = [''.join(local_lines[start:end]).rstrip('\r\n') + '\n'
                     for start, end, _ in import_spans(local)]
    previous_imports = [''.join(lines[start:end]).replace('\r\n', '\n').rstrip('\n') + '\n'
                        for start, end, _ in remote_imports]
    if local_imports != previous_imports:
        # Preserve positions/text when imports are unchanged. Changed imports form
        # a block at the first existing import, or after the module docstring.
        if remote_imports:
            edits += [(start, end, ''.join(local_imports) if i == 0 else '')
                      for i, (start, end, _) in enumerate(remote_imports)]
        else:
            tree = ast.parse(remote)
            first = tree.body[0] if tree.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                position = first.end_lineno
            elif first is not None:
                position = min([first.lineno, *(d.lineno for d in getattr(first, 'decorator_list', []))]) - 1
            else:
                position = len(lines)
            edits.append((position, position, ''.join(local_imports)))
    crlf = bool(lines and lines[0].endswith('\r\n'))
    for start, end, replacement in sorted(edits, reverse=True):
        if crlf:
            replacement = replacement.replace('\n', '\r\n')
        lines[start:end] = [replacement]
    result = ''.join(lines)
    validate(result)
    # Import edits must not introduce ambiguous bindings for the selection.
    spans(result, names)
    return result


@dataclass(frozen=True)
class ImportLink:
    statement: str
    path: Path
    source: str
    module_source: str
    status: str

    @property
    def cell(self):
        return format_link_cell(self.statement, self.source)


def synchronize(statement: str, local: str | None = None, baseline: str | None = None, expected_path: str | None = None) -> ImportLink:
    node, module = import_node(statement)
    statement = ast.unparse(node)
    path = module_path(module)
    if expected_path is not None and path != Path(expected_path):
        raise ValueError('Import resolves to a different file than the linked baseline; load a new link before editing')
    before = path.read_bytes()
    remote = before.decode('utf-8-sig')
    validate(remote, str(path))
    if isinstance(node, ast.Import):
        if local is None:
            return ImportLink(statement, path, canonical(remote), remote, 'Loaded module')
        result = sync_link(path, local, baseline)
        return ImportLink(statement, path, result.source, result.source, result.status)
    names = [alias.name for alias in node.names]
    current = selection(remote, names)
    if local is None:
        return ImportLink(statement, path, current, remote, 'Loaded selected definitions')
    local = canonical(local)
    if fingerprint(local) == fingerprint(current):
        return ImportLink(statement, path, current, remote, 'In sync')
    if fingerprint(local) == baseline:
        return ImportLink(statement, path, current, remote, 'Updated from file')
    if fingerprint(current) != baseline:
        diff = ''.join(difflib.unified_diff(current.splitlines(True), local.splitlines(True), fromfile=str(path), tofile='notebook cell'))
        raise ValueError('Sync conflict: selected definitions changed on both sides. Nothing written or executed.\n' + diff)
    merged = replace_selection(remote, local, names)
    # Preserve a UTF-8 BOM if the module originally had one.
    _replace(path, before, ('\ufeff' if before.startswith(b'\xef\xbb\xbf') else '') + merged)
    return ImportLink(statement, path, selection(merged, names), merged, 'Saved selected definitions')


def execute(link: ImportLink, namespace: dict) -> None:
    """Execute the synchronized module snapshot with normal package context."""
    node, name = import_node(link.statement)
    parent = name.rpartition('.')[0]
    if parent:
        importlib.import_module(parent)
    spec = importlib.util.spec_from_file_location(name, link.path)
    existing = sys.modules.get(name)
    module = existing if existing is not None else importlib.util.module_from_spec(spec)
    if existing is not None and Path(getattr(existing, '__file__', '')).resolve() != link.path:
        raise ValueError('Module source changed during execution setup; restart the kernel')
    sys.modules[name] = module
    try:
        exec(compile(link.module_source.encode('utf-8'), str(link.path), 'exec', dont_inherit=True), module.__dict__)
    except BaseException:
        if existing is None:
            sys.modules.pop(name, None)
        raise
    if parent:
        setattr(sys.modules[parent], name.rsplit('.', 1)[1], module)
    if isinstance(node, ast.Import):
        alias = node.names[0]
        namespace[alias.asname or name.split('.')[0]] = module if alias.asname else sys.modules[name.split('.')[0]]
    else:
        for alias in node.names:
            namespace[alias.asname or alias.name] = getattr(module, alias.name)
