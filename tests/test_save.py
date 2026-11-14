"""File safety and import advice for whole-cell promotion."""
import importlib
from pathlib import Path
import subprocess
import sys

import pytest

from load_clean.api import save_cell
from load_clean import save


def test_preview_exact_source_without_files_or_execution(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    package = tmp_path / 'preview_package'
    package.mkdir()
    marker = tmp_path / 'executed'
    (package / '__init__.py').write_text(f'open({str(marker)!r}, "w").close()\n')
    source = f'# comment\nopen({str(marker)!r}, "w").close()\n'
    before = sorted(tmp_path.rglob('*'))
    result = save_cell(package / 'helpers.py', source, preview=True)
    assert result.path == package / 'helpers.py'
    assert result.source == source
    assert sorted(tmp_path.rglob('*')) == before
    assert not marker.exists()
    assert 'preview_package' not in sys.modules
    with pytest.raises(ValueError, match='already exist'):
        save_cell(tmp_path / 'missing' / 'helpers.py', source, preview=True)
    assert not (tmp_path / 'missing').exists()


def test_create_exact_content_and_import(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    source = '# preserved café\r\ndef double(value):\r\n    return value * 2\r\n'
    result = save_cell(tmp_path / 'saved_helpers.py', source)
    assert result.path.read_bytes() == source.encode('utf-8')
    assert result.import_line == 'import saved_helpers'
    assert 'saved_helpers' not in sys.modules
    module = importlib.import_module('saved_helpers')
    try:
        assert module.double(4) == 8
    finally:
        sys.modules.pop('saved_helpers', None)


def test_package_import_and_no_initializer_execution(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(tmp_path))
    package = tmp_path / 'saved_package'
    package.mkdir()
    (package / '__init__.py').write_text('raise RuntimeError("not executed")\n')
    assert save_cell(package / 'helpers.py', 'answer = 42\n').import_line == 'import saved_package.helpers'
    assert 'saved_package' not in sys.modules


def test_source_path_and_shadowing_advice(tmp_path, monkeypatch):
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    assert save_cell(elsewhere / 'helper.py', 'value = 1\n').import_line is None
    shadow = tmp_path / 'shadow'
    shadow.mkdir()
    (shadow / 'helper.py').write_text('value = 99\n')
    monkeypatch.syspath_prepend(str(elsewhere))
    monkeypatch.syspath_prepend(str(shadow))
    assert save_cell(elsewhere / 'helper.py', 'value = 2\n', preview=True).import_line is None


def test_existing_file_refused_and_preview_allowed(tmp_path):
    path = tmp_path / 'helpers.py'
    path.write_text('# later user edits\n')
    with pytest.raises(FileExistsError):
        save_cell(path, 'value = 1\n')
    assert save_cell(path, 'value = 1\n', preview=True).source == 'value = 1\n'
    assert path.read_text() == '# later user edits\n'


@pytest.mark.parametrize('source', ['def broken(', 'return 1', '# coding: latin-1\nvalue = "café"\n'])
def test_invalid_python_leaves_existing_and_new_files_unchanged(tmp_path, source):
    existing = tmp_path / 'existing.py'
    existing.write_text('# keep\n')
    for path in (existing, tmp_path / 'new.py'):
        with pytest.raises((ValueError, SyntaxError)):
            save_cell(path, source)
    assert existing.read_text() == '# keep\n'
    assert not (tmp_path / 'new.py').exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ['existing.py']


@pytest.mark.parametrize('destination', ['helpers.txt', 'missing/helpers.py', 'folder.py'])
def test_invalid_destination(tmp_path, destination):
    (tmp_path / 'folder.py').mkdir()
    with pytest.raises(ValueError):
        save_cell(tmp_path / destination, 'value = 1\n')


def test_symlink_file_and_parent_refused(tmp_path):
    actual = tmp_path / 'actual'
    actual.mkdir()
    original = actual / 'helpers.py'
    original.write_text('# keep\n')
    (tmp_path / 'linked.py').symlink_to(original)
    (tmp_path / 'linked_parent').symlink_to(actual, target_is_directory=True)
    (tmp_path / 'dangling.py').symlink_to(actual / 'missing.py')
    for path in (tmp_path / 'linked.py', tmp_path / 'linked_parent' / 'new.py', tmp_path / 'dangling.py'):
        with pytest.raises(ValueError, match='Symlink'):
            save_cell(path, 'value = 1\n')
    assert original.read_text() == '# keep\n'
    assert not (actual / 'new.py').exists()


def test_competing_creation_never_overwrites(tmp_path, monkeypatch):
    target = tmp_path / 'helpers.py'
    link = save.os.link

    def compete(source, destination):
        target.write_text('# competing writer\n')
        link(source, destination)

    monkeypatch.setattr(save.os, 'link', compete)
    with pytest.raises(FileExistsError):
        save_cell(target, 'value = 1\n')
    assert target.read_text() == '# competing writer\n'
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize('failure', ['flush', 'publish'])
def test_failed_write_cleans_temporary_and_preserves_existing(tmp_path, monkeypatch, failure):
    original = tmp_path / 'original.py'
    original.write_text('# keep\n')

    def fail(*args):
        raise OSError('simulated write failure')

    monkeypatch.setattr(save.os, 'fsync' if failure == 'flush' else 'link', fail)
    with pytest.raises(OSError, match='simulated write failure'):
        save_cell(tmp_path / 'new.py', 'value = 1\n')
    assert list(tmp_path.iterdir()) == [original]
    assert original.read_text() == '# keep\n'


def test_core_api_has_no_ipython_dependency():
    subprocess.run([sys.executable, '-c',
                    'import sys; from load_clean.api import save_cell; '
                    'assert not any(k.startswith("IPython") for k in sys.modules)'], check=True)
