from pathlib import Path

import pytest

nbformat = pytest.importorskip('nbformat')

from load_clean.import_link import ImportLink
from load_clean_tools.cli import main
from load_clean_tools.notebook_builder import CleanOptions, build, clean_notebook, plan_build


def code(source, **kwargs):
    return nbformat.v4.new_code_cell(source, **kwargs)


def write(path, cells=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nbformat.v4.new_notebook(cells=cells or [code('value = 1')]), path)
    return path


def test_strip_header_without_loading_imports(tmp_path):
    source = '\n%%load_clean inline\nfrom missing import value\n[value]'
    nb = nbformat.v4.new_notebook(cells=[code(source)])
    clean_notebook(nb, source_roots=[tmp_path], options=CleanOptions(load_clean='strip'))
    assert nb.cells[0].source == 'from missing import value\n[value]'


def test_strip_import_link_is_explicit_snapshot_even_with_edits(tmp_path):
    body = 'def double(x):\n    return x * 2\n'
    source = ImportLink('from missing import double', tmp_path / 'missing.py', body, body, '').cell
    nb = nbformat.v4.new_notebook(cells=[code(source.replace('x * 2', 'x * 3'))])
    clean_notebook(nb, options=CleanOptions(load_clean='strip'))
    assert nb.cells[0].source == body.replace('x * 2', 'x * 3')
    assert not (tmp_path / 'missing.py').exists()


@pytest.mark.parametrize('source', [
    '%%load_clean inline\nfrom missing import value',
    '\n%%load_clean_save file.py\nvalue = 1',
    '%load_clean file.py', '%load_clean_status', '%load_clean_preview inline from missing import value',
])
def test_remove_or_keep_magic_cells(source):
    for policy in ('remove', 'keep'):
        literal = 'text = """\n%%load_clean inline\nfrom missing import value\n"""'
        nb = nbformat.v4.new_notebook(cells=[code(source), code(literal)])
        clean_notebook(nb, options=CleanOptions(load_clean=policy))
        assert [cell.source for cell in nb.cells] == ([literal] if policy == 'remove' else [source, literal])


@pytest.mark.parametrize('policy', ['resolve', 'strip'])
def test_strip_does_not_turn_writer_body_into_executed_code(policy):
    nb = nbformat.v4.new_notebook(cells=[code('%%load_clean_save file.py\nraise RuntimeError()')])
    with pytest.raises(ValueError, match='Remove the save cell'):
        clean_notebook(nb, options=CleanOptions(load_clean=policy))


def test_import_cell_removal_is_structural_and_preserves_mixed_cells():
    sources = ['# imports\nimport math\nfrom pathlib import Path',
               'import math; result = math.sqrt(4)', 'text = "import math"',
               'def f():\n    import math\n    return math.pi', '%matplotlib inline\nimport math']
    nb = nbformat.v4.new_notebook(cells=[code(source) for source in sources])
    clean_notebook(nb, options=CleanOptions(imports='remove-cells'))
    assert [cell.source for cell in nb.cells] == sources[1:]


def test_import_removal_applies_after_magic_stripping():
    nb = nbformat.v4.new_notebook(cells=[code('%%load_clean\nfrom missing import value'), code('value()')])
    clean_notebook(nb, options=CleanOptions(load_clean='strip', imports='remove-cells'))
    assert [cell.source for cell in nb.cells] == ['value()']


def test_tags_markers_setup_empty_outputs_and_metadata():
    nb = nbformat.v4.new_notebook(metadata={'custom': 'keep'}, cells=[
        code('drop = 1', metadata={'tags': ['private']}),
        code('legacy = 1 #$<AUTOREMOVE>'),
        code('# setup\n%load_ext load_clean # extension'),
        code('text = "%load_ext load_clean"'),
        code('   '),
        code('answer = 42', execution_count=3, outputs=[nbformat.v4.new_output('stream', text='42\n')], metadata={'custom': 'keep'}),
    ])
    clean_notebook(nb, options=CleanOptions(remove_tags=('private',), legacy_markers=False,
                                          strip_setup=True, drop_empty_cells=True, outputs='keep', clear_metadata=True))
    assert [cell.source for cell in nb.cells] == ['legacy = 1 #$<AUTOREMOVE>', 'text = "%load_ext load_clean"', 'answer = 42']
    assert nb.cells[-1].outputs[0].text == '42\n' and nb.cells[-1].execution_count == 3
    assert nb.metadata == {} and all(cell.metadata == {} for cell in nb.cells)


def test_keep_tagged_cells_and_custom_tags_cli(tmp_path):
    source = write(tmp_path / 'dev_x.ipynb', [code('x = 1', metadata={'tags': ['load-clean-remove']}), code('y = 2', metadata={'tags': ['private']})])
    out = tmp_path / 'out.ipynb'
    assert main(['build', str(source), '-O', str(out), '--keep-tagged-cells']) == 0
    assert len(nbformat.read(out, as_version=4).cells) == 2
    assert main(['build', str(source), '-O', str(out), '--remove-tag', 'private']) == 0
    assert nbformat.read(out, as_version=4).cells == []


def test_recursive_filters_preserve_directories_and_skip_generated_output(tmp_path):
    root = tmp_path / 'notebooks'
    good = write(root / 'a' / 'dev_one.ipynb')
    write(root / 'scratch' / 'dev_skip.ipynb')
    write(root / 'dev_two.ipynb')
    write(root / 'build' / 'dev_old.ipynb')
    tasks = plan_build([root], output=root / 'build', recursive=True, include=['*.ipynb'], exclude=['scratch/*', 'dev_two*'], suffix='_clean')
    assert tasks == [(good, root / 'build' / 'a' / 'one_clean.ipynb')]


def test_output_ancestor_does_not_hide_inputs(tmp_path):
    source = write(tmp_path / 'notebooks' / 'dev_x.ipynb')
    assert plan_build([source.parent], output=tmp_path) == [(source, tmp_path / 'x.ipynb')]


def test_cli_multiple_inputs_null_output_and_dry_run(tmp_path, capsys):
    one = write(tmp_path / 'dev_one.ipynb')
    two = write(tmp_path / 'dev_two.ipynb')
    original = [one.read_bytes(), two.read_bytes()]
    output = tmp_path / 'out'
    assert main(['build', str(one), str(two), '-o', str(output), '-n', '-0', '-v']) == 0
    captured = capsys.readouterr()
    assert captured.out == f'{output / "one.ipynb"}\0{output / "two.ipynb"}\0'
    assert 'selected 2' in captured.err and 'no output written' in captured.err
    assert not output.exists()
    assert [one.read_bytes(), two.read_bytes()] == original


def test_cli_repeated_source_quiet_and_errors(tmp_path, capsys):
    source = write(tmp_path / 'dev_x.ipynb')
    output = tmp_path / 'out'
    assert main(['build', '-s', str(source), '-s', str(source), '-o', str(output), '-q']) == 0
    assert capsys.readouterr() == ('', '')
    assert (output / 'x.ipynb').exists()
    assert main(['build', str(source), '-s', str(source), '-q']) == 1
    assert 'not both' in capsys.readouterr().err


def test_all_destinations_preflighted_before_writing(tmp_path):
    source = write(tmp_path / 'dev_a.ipynb')
    other = write(tmp_path / 'dev_b.ipynb')
    output = tmp_path / 'out'
    existing = write(output / 'b.ipynb')
    original = existing.read_bytes()
    assert main(['build', str(source), str(other), '-o', str(output), '--no-clobber']) == 1
    assert not (output / 'a.ipynb').exists() and existing.read_bytes() == original


def test_cross_input_overwrite_and_collision(tmp_path):
    first = write(tmp_path / 'dev_a.ipynb')
    second = write(tmp_path / 'a.ipynb')
    with pytest.raises(ValueError, match='overwrite an input'):
        plan_build([first, second], output=tmp_path)
    with pytest.raises(ValueError, match='collision'):
        plan_build([first, second], output=tmp_path / 'out')


def test_no_clobber_is_race_safe(tmp_path, monkeypatch):
    from load_clean_tools import notebook_builder as builder
    source = write(tmp_path / 'dev_x.ipynb')
    target = tmp_path / 'out.ipynb'
    link = builder.os.link
    def race(temporary, destination):
        target.write_text('competing output')
        return link(temporary, destination)
    monkeypatch.setattr(builder.os, 'link', race)
    with pytest.raises(FileExistsError):
        build(source, output_file=target, overwrite=False)
    assert target.read_text() == 'competing output'
    assert len(list(tmp_path.glob('*.ipynb'))) == 2


@pytest.mark.parametrize('kwargs', [
    {'check': True, 'execute': True},
    {'execute': True, 'clean_options': CleanOptions(load_clean='keep')},
    {'timeout': 10}, {'kernel': 'python3'}, {'allow_errors': True},
    {'execute': True, 'timeout': 0}, {'execute': True, 'timeout': -2},
])
def test_invalid_execution_combinations_do_not_write(tmp_path, kwargs):
    source = write(tmp_path / 'dev_x.ipynb')
    with pytest.raises(ValueError):
        build(source, output=tmp_path / 'out', **kwargs)
    assert not (tmp_path / 'out').exists()


def test_invalid_destination_options(tmp_path):
    source = write(tmp_path / 'dev_x.ipynb')
    with pytest.raises(ValueError, match='one explicitly'):
        plan_build([tmp_path], output_file=tmp_path / 'out.ipynb')
    with pytest.raises(ValueError, match='end in .ipynb'):
        plan_build([source], output_file=tmp_path / 'out.txt')
    with pytest.raises(ValueError, match='path separators'):
        plan_build([source], suffix='/outside')


def test_execution_settings_errors_and_metadata(tmp_path):
    pytest.importorskip('nbclient')
    pytest.importorskip('ipykernel')
    working = tmp_path / 'working'
    working.mkdir()
    (working / 'data.txt').write_text('content')
    source = write(tmp_path / 'dev_x.ipynb', [code('raise ValueError("expected")'), code('from pathlib import Path\nprint(Path("data.txt").read_text())')])
    original = source.read_bytes()
    target = build(source, output=tmp_path / 'out', execute=True, timeout=30, kernel='python3', execution_dir=working,
                   allow_errors=True, clean_options=CleanOptions(clear_metadata=True))
    result = nbformat.read(target, as_version=4)
    assert result.cells[0].outputs[0].output_type == 'error'
    assert result.cells[1].outputs[0].text == 'content\n'
    assert result.metadata == {} and all(cell.metadata == {} for cell in result.cells)
    assert source.read_bytes() == original


def test_execution_failure_preserves_existing_output(tmp_path):
    pytest.importorskip('nbclient')
    pytest.importorskip('ipykernel')
    source = write(tmp_path / 'dev_x.ipynb', [code('raise ValueError("expected")')])
    target = tmp_path / 'old.ipynb'
    target.write_text('previous output')
    with pytest.raises(RuntimeError, match='Execution failed'):
        build(source, output_file=target, execute=True)
    assert target.read_text() == 'previous output'
