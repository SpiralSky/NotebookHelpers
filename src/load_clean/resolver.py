from __future__ import annotations
import ast
import symtable
from pathlib import Path
from .parser import VALID_MODES, parse_import


def resolve_module(module: str) -> Path:
    # Project paths avoid executing package initializers during builds.
    import sys
    for root in sys.path:
        base = Path(root or '.') / module.replace('.', '/')
        for candidate in (base.with_suffix('.py'), base / '__init__.py'):
            if candidate.is_file():
                return candidate.resolve()
    raise ValueError(f'No Python source found for {module!r}; configure the project source path')


def _bindings(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [node.name]
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return [a.asname or (a.name.split('.')[0] if isinstance(node, ast.Import) else a.name) for a in node.names]
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if all(isinstance(t, ast.Name) for t in targets):
            return [t.id for t in targets]
    return []


def _globals(source):
    table = symtable.symtable(source, '<load_clean>', 'exec')
    names = set()
    def visit(scope):
        names.update(s.get_name() for s in scope.get_symbols() if s.is_referenced() and (scope.get_type() == 'module' or s.is_global()))
        for child in scope.get_children():
            visit(child)
    visit(table)
    identifiers = {n.id for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Name)}
    return names & identifiers


class LoadCleanResolver:
    def resolve(self, import_line, names, mode='default'):
        if mode not in VALID_MODES:
            raise ValueError(f'Unknown mode {mode!r}')
        module, targets, wildcard, _ = parse_import(import_line)
        if mode == 'default':
            return import_line
        if isinstance(ast.parse(import_line).body[0], ast.Import):
            raise ValueError('Embedding requires from module import symbol syntax')
        path = resolve_module(module)
        source = path.read_text(encoding='utf-8')
        tree = ast.parse(source)
        index = {}
        for node in tree.body:
            for name in _bindings(node):
                if name in index:
                    raise ValueError(f'Ambiguous repeated definition: {name}')
                index[name] = node
        requested = names or list(targets)
        if wildcard and not requested:
            raise ValueError('Wildcard embedding requires an explicit symbol list')
        inverse = {alias: original for original, alias in targets.items()}
        requested = [inverse.get(n, n) for n in requested]
        selected = set()
        import builtins
        def include(name):
            if name not in index:
                if name in vars(builtins):
                    return
                raise ValueError(f'Unresolved dependency {name!r} in {path}')
            node = index[name]
            if node in selected:
                return
            if isinstance(node, ast.ImportFrom) and (node.level or any(a.name == '*' for a in node.names)):
                raise ValueError('Relative and wildcard dependency imports cannot be embedded')
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id in {'eval', 'exec', 'globals', 'locals', '__import__'}:
                    raise ValueError(f'Dynamic dependency lookup {child.func.id!r} cannot be embedded')
            selected.add(node)
            for dependency in _globals(ast.unparse(node)) - set(_bindings(node)):
                include(dependency)
        for name in requested:
            if name not in index:
                raise ValueError(f'Symbol {name!r} not found in {path}')
            include(name)
        nodes = [n for n in tree.body if n in selected or isinstance(n, ast.ImportFrom) and n.module == '__future__']
        if mode == 'skeleton':
            class Stub(ast.NodeTransformer):
                def visit_FunctionDef(self, node):
                    node.body = [ast.Raise(exc=ast.Call(func=ast.Name(id='NotImplementedError', ctx=ast.Load()), args=[], keywords=[]), cause=None)]
                    return node
                visit_AsyncFunctionDef = visit_FunctionDef
            nodes = [Stub().visit(n) for n in nodes]
        result = ast.unparse(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])))
        for name in requested:
            alias = targets.get(name, name)
            if alias != name:
                result += f'\n{alias} = {name}'
        compile(result, str(path), 'exec')
        return result
