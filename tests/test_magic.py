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
