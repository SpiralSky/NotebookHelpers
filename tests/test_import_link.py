import sys

import pytest

from load_clean.import_link import execute, fingerprint, parse_link_header, synchronize


@pytest.fixture
def module(tmp_path, monkeypatch):
    package = tmp_path / 'linked_project'
    package.mkdir()
    (package / '__init__.py').write_text('')
    (package / 'utilities.py').write_text('FACTOR = 2\n')
    source = package / 'helpers.py'
    source.write_text('from .utilities import FACTOR\n\n# retain this comment\ndef double(x):\n    return x * FACTOR\n\n# unrelated code\ndef other():\n    return 10\n')
    monkeypatch.syspath_prepend(str(tmp_path))
    yield source
    for name in list(sys.modules):
        if name == 'linked_project' or name.startswith('linked_project.'):
            sys.modules.pop(name)


def sync_edit(link, source):
    return synchronize(link.statement, source, fingerprint(link.source), str(link.path))


def test_selected_import_executes_with_package_dependencies_and_alias(module):
    link = synchronize('from linked_project.helpers import double as twice')
    assert link.source.startswith('def double(')
    assert 'other' not in link.source and 'FACTOR = ' not in link.source
    namespace = {}
    execute(link, namespace)
    assert namespace['twice'](5) == 10
    assert namespace['twice'].__module__ == 'linked_project.helpers'
    assert set(namespace) == {'twice'}
    assert parse_link_header(link.cell.split('\n', 1)[0][len('%%load_clean '):]) == (
        link.statement, str(module), fingerprint(link.source))


def test_selected_write_preserves_unrelated_source_and_external_edits(module):
    link = synchronize('from linked_project.helpers import double')
    original = module.read_text()
    module.write_text(original.replace('return 10', 'return 99'))
    result = sync_edit(link, link.source.replace('x * FACTOR', 'x * FACTOR + 1'))
    assert result.status == 'Saved selected definitions'
    assert module.read_text() == original.replace('return 10', 'return 99').replace('x * FACTOR', 'x * FACTOR + 1')
    namespace = {}
    execute(result, namespace)
    assert namespace['double'](3) == 7


def test_selected_conflict_does_not_modify_file(module):
    link = synchronize('from linked_project.helpers import double')
    changed = module.read_text().replace('x * FACTOR', 'x * 3')
    module.write_text(changed)
    with pytest.raises(ValueError, match='Sync conflict'):
        sync_edit(link, link.source.replace('x * FACTOR', 'x * 4'))
    assert module.read_text() == changed
    assert 'linked_project.helpers' not in sys.modules
    refreshed = sync_edit(link, link.source)
    assert 'x * 3' in refreshed.source


def test_dependency_only_change_uses_current_module(module):
    link = synchronize('from linked_project.helpers import double')
    module.write_text(module.read_text().replace('from .utilities import FACTOR', 'FACTOR = 5'))
    current = sync_edit(link, link.source)
    namespace = {}
    execute(current, namespace)
    assert namespace['double'](3) == 15


@pytest.mark.parametrize('statement, binding', [
    ('import linked_project.helpers as helpers', 'helpers'),
    ('import linked_project.helpers', 'linked_project'),
])
def test_module_import_and_edits(module, statement, binding):
    link = synchronize(statement)
    result = sync_edit(link, link.source.replace('return 10', 'return 42'))
    namespace = {}
    execute(result, namespace)
    target = namespace[binding] if binding == 'helpers' else namespace[binding].helpers
    assert target.other() == 42 and target.double(4) == 8


def test_multiple_selected_names_preserve_file_order(module):
    link = synchronize('from linked_project.helpers import other as another, double')
    assert link.source.index('def double') < link.source.index('def other')
    result = sync_edit(link, link.source.replace('return 10', 'return 9').replace('x * FACTOR', 'x * FACTOR + 1'))
    namespace = {}
    execute(result, namespace)
    assert namespace['another']() == 9 and namespace['double'](2) == 5


def test_classes_constants_and_decorators(module):
    module.write_text('def deco(fn):\n    return fn\n\n@deco\ndef double(x):\n    # keep internal comment\n    return x * 2\n\nVALUE: int = 4\n\nclass Thing:\n    def run(self):\n        return VALUE\n')
    link = synchronize('from linked_project.helpers import double, Thing, VALUE')
    assert link.source.startswith('@deco\n')
    result = sync_edit(link, link.source.replace('VALUE: int = 4', 'VALUE: int = 7'))
    namespace = {}
    execute(result, namespace)
    assert namespace['Thing']().run() == 7
    assert '# keep internal comment' in module.read_text()


@pytest.mark.parametrize('source', [
    'def double(x): return x\ndef double(x): return x * 2\n',
    'from .utilities import FACTOR as double\n',
    'if True:\n    def double(x): return x\n',
    'double = 1; other = 2\n',
    'double = 1\nif True:\n    double = 2\n',
    'def double(x): return x\nfrom .utilities import *\n',
])
def test_unsafe_selection_refused(module, source):
    module.write_text(source)
    with pytest.raises(ValueError):
        synchronize('from linked_project.helpers import double')
    assert module.read_text() == source


@pytest.mark.parametrize('edit', [
    'import math\ndef double(x):\n    return x\n',
    'def renamed(x):\n    return x\n',
    '# unattached comment\ndef double(x):\n    return x\n',
    'def double(',
])
def test_invalid_edits_preserve_module(module, edit):
    link = synchronize('from linked_project.helpers import double')
    original = module.read_bytes()
    with pytest.raises((SyntaxError, ValueError)):
        sync_edit(link, edit)
    assert module.read_bytes() == original


def test_import_target_relocation_refused(module):
    link = synchronize('from linked_project.helpers import double')
    with pytest.raises(ValueError, match='different file'):
        synchronize(link.statement, link.source, fingerprint(link.source), str(module.parent / 'another.py'))


def test_selection_preserves_crlf_and_bom(module):
    original = module.read_text().replace('\n', '\r\n').encode()
    module.write_bytes(b'\xef\xbb\xbf' + original)
    link = synchronize('from linked_project.helpers import double')
    sync_edit(link, link.source.replace('x * FACTOR', 'x * FACTOR + 1'))
    assert module.read_bytes() == b'\xef\xbb\xbf' + original.replace(b'x * FACTOR', b'x * FACTOR + 1')


@pytest.mark.parametrize('statement', ['from linked_project.helpers import *', 'from .helpers import double', 'import linked_project, sys', 'from linked_project.helpers import double, double'])
def test_ambiguous_imports_refused(module, statement):
    with pytest.raises(ValueError):
        synchronize(statement)
