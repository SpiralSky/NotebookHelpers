import ast
import sys
import pytest
from load_clean.api import resolve_cell
from load_clean.parser import parse_load_clean_cell

@pytest.fixture
def module(tmp_path, monkeypatch):
    (tmp_path / 'review_example.py').write_text('import math\nOFFSET: int = 7\ndef f(x):\n    return math.sqrt(x) + OFFSET\nclass C:\n    def method(self): return 1\ndef one(): return 1\n')
    monkeypatch.syspath_prepend(str(tmp_path))
    return 'review_example'

def test_default_preserves_import(module):
    statement = f'from {module} import f as alias'
    assert resolve_cell(statement, []) == statement

def test_dependency_closure_and_alias(module):
    source = resolve_cell(f'from {module} import f as alias', [], 'inline')
    ns = {}
    exec(source, ns)
    assert ns['alias'](4) == 9

def test_skeleton_valid_and_explicit(module):
    source = resolve_cell(f'from {module} import C, one', [], 'skeleton')
    ns = {}
    exec(source, ns)
    with pytest.raises(NotImplementedError): ns['C']().method()
    with pytest.raises(NotImplementedError): ns['one']()

def test_missing_symbol_errors(module):
    with pytest.raises(ValueError, match='not found'):
        resolve_cell(f'from {module} import missing', [], 'inline')

def test_annotated_assignment(module):
    ns = {}
    exec(resolve_cell(f'from {module} import OFFSET', [], 'inline'), ns)
    assert ns['OFFSET'] == 7

def test_shared_header_parser():
    parsed = parse_load_clean_cell('%%load_clean inline from example import f\n[f]')
    assert parsed.mode == 'inline' and parsed.names == ['f']

def test_edited_body_rejected():
    with pytest.raises(ValueError, match='materialize'):
        parse_load_clean_cell('%%load_clean inline\nfrom example import f\ndef f(): pass')

def test_parent_initializer_not_executed(tmp_path, monkeypatch):
    package = tmp_path / 'side_effect_package'
    package.mkdir()
    (package / '__init__.py').write_text('raise RuntimeError("must not execute")')
    (package / 'helpers.py').write_text('def f(): return 1')
    monkeypatch.syspath_prepend(str(tmp_path))
    assert 'def f' in resolve_cell('from side_effect_package.helpers import f', [], 'inline')

def test_dynamic_lookup_rejected(tmp_path, monkeypatch):
    (tmp_path / 'dynamic_example.py').write_text('def f(): return globals()["hidden"]')
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(ValueError, match='Dynamic dependency'):
        resolve_cell('from dynamic_example import f', [], 'inline')

def test_nested_scope_does_not_hide_global(tmp_path, monkeypatch):
    (tmp_path / 'scope_example.py').write_text('VALUE = 9\ndef f():\n    def inner(VALUE): return VALUE\n    return VALUE\n')
    monkeypatch.syspath_prepend(str(tmp_path))
    ns = {}
    exec(resolve_cell('from scope_example import f', [], 'inline'), ns)
    assert ns['f']() == 9


def test_explicit_source_roots_are_exclusive_and_static(tmp_path, monkeypatch):
    root = tmp_path / 'explicit'
    root.mkdir()
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    (root / 'selection.py').write_text('raise RuntimeError("must not import")\ndef f(): return 9')
    (elsewhere / 'selection.py').write_text('def f(): return 1')
    (elsewhere / 'only_elsewhere.py').write_text('def f(): return 2')
    monkeypatch.syspath_prepend(str(elsewhere))
    before = list(sys.path)
    source = resolve_cell('from selection import f', [], 'inline', source_roots=[root])
    assert 'return 9' in source
    with pytest.raises(ValueError, match='--source-root'):
        resolve_cell('from only_elsewhere import f', [], 'inline', source_roots=[root])
    assert sys.path == before and 'selection' not in sys.modules


@pytest.mark.parametrize('mode', ['copy', 'skeleton'])
def test_copy_import_policy(module, mode):
    source = resolve_cell(f'from {module} import f', [], mode)
    assert 'import math' not in source
    included = resolve_cell(f'from {module} import f', [], mode, include_imports=True)
    assert 'import math' in included
    if mode == 'copy':
        namespace = {}
        exec(included, namespace)
        assert namespace['f'](4) == 9


@pytest.mark.parametrize('header', ['copy --include-imports', '--include-imports copy'])
def test_include_imports_parser(header):
    parsed = parse_load_clean_cell(f'%%load_clean {header}\nfrom example import f')
    assert parsed.mode == 'copy' and parsed.include_imports
