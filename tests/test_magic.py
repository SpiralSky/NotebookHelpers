import sys

import pytest
from IPython.core.error import UsageError
from IPython.core.interactiveshell import InteractiveShell

from load_clean.extension import load_ipython_extension


@pytest.fixture
def shell(tmp_path, monkeypatch):
    (tmp_path / 'magic_example.py').write_text('VALUE = 3\ndef answer():\n    return VALUE\n')
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop('magic_example', None)
    shell = InteractiveShell(user_ns={})
    load_ipython_extension(shell)
    yield shell
    sys.modules.pop('magic_example', None)


def test_default_import_uses_own_shell_and_preserves_cell(shell, monkeypatch):
    monkeypatch.setattr(shell, 'set_next_input', lambda *a, **k: pytest.fail('rewrote cell'))
    shell.run_cell_magic('load_clean', '', 'import magic_example as example')
    assert shell.user_ns['example'].answer() == 3
    assert 'answer' not in shell.user_ns


def test_inline_and_preview(shell, capsys):
    shell.run_line_magic('load_clean_preview', 'inline from magic_example import answer')
    assert 'def answer' in capsys.readouterr().out
    assert 'answer' not in shell.user_ns
    shell.run_cell_magic('load_clean', 'inline', 'from magic_example import answer')
    assert shell.user_ns['answer']() == 3


def test_status_detects_source_change(shell, tmp_path, capsys):
    shell.run_cell_magic('load_clean', 'inline', 'from magic_example import answer')
    shell.run_line_magic('load_clean_status', '')
    assert 'unchanged sha256:' in capsys.readouterr().out
    (tmp_path / 'magic_example.py').write_text('VALUE = 4\n')
    shell.run_line_magic('load_clean_status', '')
    assert 'changed sha256:' in capsys.readouterr().out
    shell.run_line_magic('load_clean_check', 'inline from magic_example import VALUE')
    assert 'valid sha256:' in capsys.readouterr().out


def test_invalid_input_is_usage_error(shell):
    with pytest.raises(UsageError):
        shell.run_cell_magic('load_clean', 'inline', 'x = 1')


def test_materialize_creates_new_input(shell, monkeypatch):
    calls = []
    monkeypatch.setattr(shell, 'set_next_input', lambda source, replace: calls.append((source, replace)))
    shell.run_line_magic('load_clean_materialize', 'inline from magic_example import answer')
    assert 'def answer' in calls[0][0]
    assert calls[0][1] is False
    assert 'answer' not in shell.user_ns


def test_save_preview_and_create_preserve_shell(shell, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(shell, 'set_next_input', lambda *a, **k: pytest.fail('rewrote cell'))
    marker = tmp_path / 'body_executed'
    source = f'# exact comment\nopen({str(marker)!r}, "w").close()\nanswer = 42\n'
    path = tmp_path / 'saved_magic.py'
    before = dict(shell.user_ns)
    shell.run_cell_magic('load_clean_save', f'--preview {path}', source)
    assert capsys.readouterr().out == f'Preview destination: {path}\nExact source follows:\n{source}'
    assert not path.exists() and not marker.exists()
    shell.run_cell_magic('load_clean_save', str(path), source)
    assert path.read_bytes() == source.encode('utf-8')
    assert 'import saved_magic' in capsys.readouterr().out
    assert not marker.exists()
    assert shell.user_ns == before
    path.write_text('# later edit\n')
    with pytest.raises(UsageError, match='already exists'):
        shell.run_cell_magic('load_clean_save', str(path), source)
    assert path.read_text() == '# later edit\n'


@pytest.mark.parametrize('line, source', [('', 'x = 1'), ('--replace x.py', 'x = 1'), ('x.py', 'def bad(')])
def test_save_errors_are_usage_errors(shell, line, source):
    with pytest.raises(UsageError):
        shell.run_cell_magic('load_clean_save', line, source)


def test_edit_reload_and_inline_rerun(shell, tmp_path, capsys):
    import importlib

    shell.run_cell_magic('load_clean', '', 'import magic_example as ordinary')
    shell.run_cell_magic('load_clean', 'inline', 'from magic_example import answer')
    ordinary = shell.user_ns['ordinary']
    old_answer = shell.user_ns['answer']
    old_result = old_answer()
    (tmp_path / 'magic_example.py').write_text('VALUE = 12345\ndef answer():\n    return VALUE\n')
    shell.run_cell_magic('load_clean', '', 'import magic_example as ordinary')
    assert ordinary.answer() == 3 and old_answer() == 3
    importlib.invalidate_caches()
    importlib.reload(ordinary)
    assert ordinary.answer() == 12345 and old_answer() == 3
    shell.run_line_magic('load_clean_status', '')
    assert 'cannot certify downstream results' in capsys.readouterr().out
    shell.run_cell_magic('load_clean', 'inline', 'from magic_example import answer')
    assert shell.user_ns['answer']() == 12345
    assert old_result == 3
