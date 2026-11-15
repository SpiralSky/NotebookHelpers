from __future__ import annotations
import ast
from .models import LoadCleanCell
VALID_MODES = {'copy', 'skeleton', 'default', 'inline'}

def parse_import(line):
    try:
        nodes = ast.parse(line).body
    except SyntaxError as exc:
        raise ValueError('Expected one valid Python import') from exc
    if len(nodes) != 1:
        raise ValueError('Expected exactly one import')
    node = nodes[0]
    if isinstance(node, ast.Import) and len(node.names) == 1:
        return node.names[0].name, {}, False, line
    if isinstance(node, ast.ImportFrom) and node.module and not node.level:
        return node.module, {a.name: a.asname or a.name for a in node.names if a.name != '*'}, any(a.name == '*' for a in node.names), line
    raise ValueError('Only absolute, single-module imports are supported')

def parse_line(line, cell):
    parts = line.strip().split(None, 1)
    mode = parts.pop(0) if parts and parts[0] in VALID_MODES else 'default'
    header = parts[0] if parts else ''
    return mode, header or next((s.strip() for s in cell.splitlines() if s.strip()), '')

def is_load_clean_cell(source):
    lines = source.lstrip().splitlines()
    return bool(lines and lines[0].strip().split(None, 1)[0:1] == ['%%load_clean'])

def parse_load_clean_cell(source):
    if not is_load_clean_cell(source):
        return None
    lines = source.lstrip().splitlines()
    header = lines[0].strip()[len('%%load_clean'):].strip()
    include_imports = '--include-imports' in header.split()
    header = header.replace('--include-imports', '') if include_imports else header
    parts = header.split(None, 1)
    mode = parts.pop(0) if parts and parts[0] in VALID_MODES else 'default'
    body = '\n'.join(lines[1:])
    if parts:
        body = parts[0] + '\n' + body
    try:
        tree = ast.parse(body)
    except SyntaxError as exc:
        raise ValueError('Invalid load_clean cell') from exc
    if not tree.body or not isinstance(tree.body[0], (ast.Import, ast.ImportFrom)):
        raise ValueError('load_clean requires an import statement')
    import_line = ast.unparse(tree.body[0])
    parse_import(import_line)
    names = []
    for node in tree.body[1:]:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.List) or any(not isinstance(x, ast.Name) for x in node.value.elts):
            raise ValueError('Only an import and optional symbol list are allowed; materialize generated code before editing')
        names.extend(x.id for x in node.value.elts)
    return LoadCleanCell(mode, import_line, names, include_imports)
