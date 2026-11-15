from pathlib import Path

import pytest

from load_clean.linked import fingerprint, load_link, parse_header, sync_link


BASE = 'import math\n\ndef answer():\n    return math.sqrt(9)\n'
LOCAL = BASE.replace('sqrt(9)', 'sqrt(16)')
REMOTE = BASE.replace('sqrt(9)', 'sqrt(25)')


@pytest.fixture
def path(tmp_path):
    path = tmp_path / 'helper with spaces.py'
    path.write_text(BASE)
    return path


@pytest.mark.parametrize('local, remote, status, expected', [
    (BASE, BASE, 'In sync', BASE),
    (LOCAL, BASE, 'Saved to file', LOCAL),
    (BASE, REMOTE, 'Updated from file', REMOTE),
    (LOCAL, LOCAL, 'In sync', LOCAL),
])
def test_sync_directions(path, local, remote, status, expected):
    path.write_text(remote)
    result = sync_link(path, local, fingerprint(BASE))
    assert result.source == expected and result.status == status
    assert path.read_text() == expected
    filename, baseline = parse_header(result.cell.splitlines()[0][len('%%load_clean '):])
    assert Path(filename) == path and baseline == fingerprint(expected)


def test_conflict_preserves_file_and_reports_diff(path):
    path.write_text(REMOTE)
    with pytest.raises(ValueError, match='Sync conflict') as error:
        sync_link(path, LOCAL, fingerprint(BASE))
    assert '-    return math.sqrt(25)' in str(error.value)
    assert '+    return math.sqrt(16)' in str(error.value)
    assert path.read_text() == REMOTE


def test_load_and_restart_baseline(path):
    loaded = load_link(path)
    header, body = loaded.cell.split('\n', 1)
    filename, baseline = parse_header(header[len('%%load_clean '):])
    # No kernel-side state is needed to resolve changes after restart.
    path.write_text(REMOTE)
    assert sync_link(filename, body, baseline).source == REMOTE


def test_no_baseline_never_overwrites_existing(path):
    with pytest.raises(ValueError, match='no baseline'):
        sync_link(path, LOCAL)
    assert path.read_text() == BASE
    assert sync_link(path, BASE).status == 'In sync'


def test_create_and_deleted_link(tmp_path):
    path = tmp_path / 'new.py'
    assert sync_link(path, BASE).status == 'Created file'
    path.unlink()
    with pytest.raises(ValueError, match='deleted'):
        sync_link(path, LOCAL, fingerprint(BASE))
    assert not path.exists()


@pytest.mark.parametrize('source', ['def broken(', '# coding: latin-1\nx = 1'])
def test_invalid_edits_do_not_write(path, source):
    with pytest.raises((ValueError, SyntaxError)):
        sync_link(path, source, fingerprint(BASE))
    assert path.read_text() == BASE


def test_invalid_source_update_does_not_change_baseline(path):
    path.write_text('def broken(')
    with pytest.raises(SyntaxError):
        sync_link(path, BASE, fingerprint(BASE))
    assert path.read_text() == 'def broken('


def test_newline_normalization_does_not_rewrite_file(path):
    original = BASE.replace('\n', '\r\n').encode() + b'\r\n'
    path.write_bytes(original)
    assert sync_link(path, BASE.rstrip('\n'), fingerprint(BASE)).status == 'In sync'
    assert path.read_bytes() == original


def test_utf8_bom_load_runs_without_rewriting_file(path):
    original = b'\xef\xbb\xbf' + BASE.encode()
    path.write_bytes(original)
    result = load_link(path)
    namespace = {}
    exec(result.source, namespace)
    assert namespace['answer']() == 3
    assert sync_link(path, result.source, fingerprint(result.source)).status == 'In sync'
    assert path.read_bytes() == original


def test_symlink_refusal(path, tmp_path):
    link = tmp_path / 'link.py'
    link.symlink_to(path)
    with pytest.raises(ValueError, match='Symlink'):
        sync_link(link, LOCAL, fingerprint(BASE))
    assert path.read_text() == BASE


def test_concurrent_edit_before_publication(path, monkeypatch):
    from load_clean import linked
    chmod = linked.os.chmod

    def change_source(*args):
        chmod(*args)
        path.write_text(REMOTE)

    monkeypatch.setattr(linked.os, 'chmod', change_source)
    with pytest.raises(ValueError, match='during synchronization'):
        sync_link(path, LOCAL, fingerprint(BASE))
    assert path.read_text() == REMOTE
    assert not list(path.parent.glob('.load-clean-*'))


def test_replace_failure_preserves_source(path, monkeypatch):
    from load_clean import linked

    def fail(*args):
        raise OSError('failed publication')

    monkeypatch.setattr(linked.os, 'replace', fail)
    with pytest.raises(OSError, match='failed publication'):
        sync_link(path, LOCAL, fingerprint(BASE))
    assert path.read_text() == BASE
    assert not list(path.parent.glob('.load-clean-*'))


def test_permissions_preserved(path):
    path.chmod(0o640)
    sync_link(path, LOCAL, fingerprint(BASE))
    assert path.stat().st_mode & 0o777 == 0o640


@pytest.mark.parametrize('header', ['x.py --base invalid', 'x.py --force', 'x.txt', 'x.py --base ' + '0' * 64 + ' extra'])
def test_invalid_header(header):
    with pytest.raises(ValueError):
        parse_header(header)


def test_missing_parent_and_invalid_extension(tmp_path):
    for path in (tmp_path / 'missing' / 'file.py', tmp_path / 'file.txt'):
        with pytest.raises(ValueError):
            sync_link(path, BASE)
