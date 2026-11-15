from __future__ import annotations

import io
import ast
from dataclasses import dataclass
from fnmatch import fnmatchcase
import os
import shlex
from pathlib import Path
import tempfile
import tokenize
from typing import Any

from load_clean.api import resolve_cell
from load_clean.parser import parse_load_clean_cell
from load_clean.linked import parse_header, validate
from load_clean.linked import fingerprint
from load_clean._import_link_format import parse_link_cell, protected_import


@dataclass(frozen=True)
class CleanOptions:
    load_clean: str = 'resolve'
    imports: str = 'keep'
    outputs: str = 'clear'
    remove_tags: tuple[str, ...] = ('load-clean-remove',)
    legacy_markers: bool = True
    strip_setup: bool = False
    clear_metadata: bool = False
    drop_empty_cells: bool = False

    def __post_init__(self):
        for name, choices in (
            ('load_clean', {'resolve', 'strip', 'remove', 'keep'}),
            ('imports', {'keep', 'remove-cells'}),
            ('outputs', {'clear', 'keep'}),
        ):
            if getattr(self, name) not in choices:
                raise ValueError(f'Invalid {name} policy: {getattr(self, name)}')


def _command(source: str) -> str:
    first = source.lstrip().splitlines()[0:1]
    return first[0].split(None, 1)[0] if first else ''


def _load_clean_command(source: str) -> bool:
    return _command(source) in {
        '%%load_clean', '%%load_clean_save', '%load_clean', '%load_clean_preview',
        '%load_clean_materialize', '%load_clean_check', '%load_clean_status',
    }


def _setup_cell(source: str) -> bool:
    lines = [line.strip() for line in source.splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if len(lines) != 1:
        return False
    try:
        return shlex.split(lines[0], comments=True) in [
            ['%load_ext', 'load_clean'], ['%reload_ext', 'load_clean'],
        ]
    except ValueError:
        return False


def _import_only(source: str) -> bool:
    try:
        nodes = ast.parse(source).body
    except SyntaxError:
        return False
    return bool(nodes) and all(isinstance(node, (ast.Import, ast.ImportFrom)) for node in nodes)


def _dependency(name: str, extra: str = "tools") -> Any:
    try:
        return __import__(name)
    except ImportError as exc:
        raise RuntimeError(f"{name} is required; install load-clean[{extra}] from a source checkout with python -m pip install -e '.[{extra}]'") from exc


def is_autoremove_cell(source: str) -> bool:
    """Recognize the legacy marker only when it is an exact Python comment."""
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT and token.string.strip() == "#$<AUTOREMOVE>":
                return True
    except (tokenize.TokenError, IndentationError):
        pass
    return False


def resolve_cells(notebook: Any, *, source_roots: list[str | Path] | None = None, cell_numbers: list[int] | None = None, policy: str = 'resolve') -> Any:
    """Replace code cells containing load-clean magic with resolved source."""
    for index, cell in zip(cell_numbers or range(1, len(notebook.cells) + 1), notebook.cells):
        if cell.cell_type != "code":
            continue
        if policy == 'keep':
            continue
        try:
            # IPython ignores leading blank lines before recognizing cell magics.
            first_line = cell.source.lstrip().splitlines()[0:1]
            if first_line and first_line[0].strip().split(None, 1)[0:1] == ["%%load_clean_save"]:
                raise ValueError("Remove the save cell or tag it load-clean-remove before export")
            if first_line and first_line[0].strip().split(None, 1)[0:1] == ["%load_clean"]:
                raise ValueError("Remove the file-loading command cell or tag it load-clean-remove before export; keep the generated linked cell")
            if first_line and first_line[0].strip().split(None, 1)[0:1] == ["%%load_clean"]:
                header, _, body = cell.source.lstrip().partition('\n')
                if policy == 'strip':
                    validate(body)
                    cell.source = body
                    continue
                line = header.strip()[len('%%load_clean'):].strip()
                imported = parse_link_cell(line, body)
                if imported is not None:
                    statement, _, baseline, source = imported
                    if fingerprint(source) != baseline:
                        raise ValueError('Import-linked cell has unsynchronized edits; run it and save the notebook before export')
                    cell.source = protected_import(statement)
                    continue
                if not line:
                    cell.source = protected_import(body)
                    continue
                if parse_header(line) is not None:
                    # Export the saved notebook snapshot; never synchronize or
                    # access the linked file during a static check/build.
                    cell.source = validate(body)
                    continue
            parsed = parse_load_clean_cell(cell.source)
            if parsed:
                cell.source = resolve_cell(parsed.import_line, parsed.names, parsed.mode, source_roots=source_roots)
        except Exception as exc:
            raise ValueError(f"Cell {index}: {exc}. For unsupported embedding, keep an ordinary import in default mode and install the helper in the runtime environment.") from exc
    return notebook


def clean_notebook(notebook: Any, *, source_roots: list[str | Path] | None = None, options: CleanOptions | None = None) -> Any:
    """Remove marked cells, resolve magic, and clear execution state."""
    options = options or CleanOptions()
    retained = [(index, cell) for index, cell in enumerate(notebook.cells, 1) if not (
        set(options.remove_tags).intersection(cell.get("metadata", {}).get("tags", []))
        or (cell.cell_type == "code" and options.legacy_markers and is_autoremove_cell(cell.source))
        or (cell.cell_type == "code" and options.load_clean == 'remove' and _load_clean_command(cell.source))
        or (cell.cell_type == "code" and options.strip_setup and _setup_cell(cell.source))
    )]
    notebook.cells = [cell for _, cell in retained]
    resolve_cells(notebook, source_roots=source_roots, cell_numbers=[index for index, _ in retained], policy=options.load_clean)
    notebook.cells = [cell for cell in notebook.cells if not (
        options.imports == 'remove-cells' and cell.cell_type == 'code' and _import_only(cell.source)
        or options.drop_empty_cells and not cell.source.strip()
    )]
    for cell in notebook.cells:
        if cell.cell_type == "code" and options.outputs == 'clear':
            cell.outputs = []
            cell.execution_count = None
        if options.clear_metadata:
            cell.metadata = {}
    if options.clear_metadata:
        notebook.metadata = {}
    return notebook


def load_source_notebook(path: Path) -> Any:
    """Read the explicitly selected ipynb or py:percent source."""
    if path.suffix == ".ipynb":
        return _dependency("nbformat").read(path, as_version=4)
    if path.suffix == ".py":
        return _dependency("jupytext").read(path, fmt="py:percent")
    raise ValueError(f"Unsupported notebook source: {path}; select .ipynb or py:percent")


def find_notebook(source: Path) -> Path:
    """Return the explicitly selected notebook path."""
    return source


def _target(source: Path, output: str | Path, prefix: str, suffix: str = '') -> Path:
    if '/' in suffix or '\\' in suffix:
        raise ValueError('Output suffix must not contain path separators')
    return Path(output) / f"{source.stem.removeprefix(prefix)}{suffix}.ipynb"


def _validate_paths(sources: list[Path], output: str | Path, prefix: str) -> None:
    _validate_tasks([(source, _target(source, output, prefix)) for source in sources], prefix=prefix)


def _validate_tasks(tasks: list[tuple[Path, Path]], *, prefix: str = 'dev_', suffix: str = '', overwrite: bool = True) -> None:
    targets: dict[Path, Path] = {}
    inputs = {source.resolve() for source, _ in tasks}
    for source, destination in tasks:
        if destination.suffix != '.ipynb':
            raise ValueError(f'Output filename must end in .ipynb: {destination}')
        target = destination.resolve()
        if target in inputs:
            raise ValueError(f"Output would overwrite an input notebook: {target}")
        if target in targets:
            previous = targets[target]
            detail = ""
            if previous.with_suffix("") == source.with_suffix("") and {previous.suffix, source.suffix} == {".py", ".ipynb"}:
                choices = [shlex.join(["load-clean", "build", "--source", str(path), "--output", str(destination.parent), "--prefix", prefix] + (["--suffix", suffix] if suffix else [])) for path in (previous, source)]
                detail = f"; paired source ambiguity. Select the intended saved input explicitly: {choices[0]} OR {choices[1]}. Build does not synchronize; reconcile copies or deliberately sync first."
            raise ValueError(f"Output collision: {previous} and {source} both map to {target}{detail}")
        targets[target] = source
        if not overwrite and (destination.exists() or destination.is_symlink()):
            raise FileExistsError(f'Output exists (--no-clobber): {destination}')


def plan_build(sources: list[str | Path], *, output: str | Path = 'build', output_file: str | Path | None = None,
               prefix: str = 'dev_', suffix: str = '', recursive: bool = False,
               include: list[str] | None = None, exclude: list[str] | None = None,
               overwrite: bool = True) -> list[tuple[Path, Path]]:
    """Discover all inputs and validate every destination before any writes."""
    tasks = []
    seen = set()
    output_root = Path(output).resolve()
    patterns = include if include is not None else [f'{prefix}*.py', f'{prefix}*.ipynb']
    for value in sources:
        source = Path(value)
        if not source.exists():
            raise FileNotFoundError(f'Source does not exist: {source}; select an existing saved file or directory')
        if source.is_file():
            candidates = [(source, Path(output))]
        else:
            candidates = []
            for path in sorted(source.rglob('*') if recursive else source.glob('*')):
                if not path.is_file() or path.suffix not in {'.py', '.ipynb'}:
                    continue
                if source.resolve() in output_root.parents and output_root in path.resolve().parents:
                    continue
                relative = path.relative_to(source)
                matches = lambda pattern: fnmatchcase(relative.as_posix(), pattern) or fnmatchcase(path.name, pattern)
                if not any(matches(pattern) for pattern in patterns) or any(matches(pattern) for pattern in exclude or []):
                    continue
                candidates.append((path, Path(output) / relative.parent))
            if not candidates:
                raise ValueError(f'No notebooks matching {patterns} in {source}')
        for path, directory in candidates:
            if path.suffix not in {'.py', '.ipynb'}:
                raise ValueError(f'Unsupported notebook source: {path}; select .ipynb or py:percent')
            if path.resolve() in seen:
                continue
            seen.add(path.resolve())
            tasks.append((path, _target(path, directory, prefix, suffix)))
    if output_file is not None:
        if len(sources) != 1 or not Path(sources[0]).is_file():
            raise ValueError('--output-file requires one explicitly selected source file')
        tasks = [(tasks[0][0], Path(output_file))]
    if not tasks:
        raise ValueError('No notebooks selected')
    _validate_tasks(tasks, prefix=prefix, suffix=suffix, overwrite=overwrite)
    return tasks


def _execute(notebook: Any, source: Path, *, timeout: int | None = None, kernel: str | None = None,
             execution_dir: str | Path | None = None, allow_errors: bool = False) -> None:
    try:
        from nbclient import NotebookClient
    except ImportError as exc:
        raise RuntimeError("nbclient is required for --execute; install nbclient and an IPython kernel") from exc
    kwargs = dict(timeout=timeout, allow_errors=allow_errors)
    if kernel is not None:
        kwargs['kernel_name'] = kernel
    directory = Path(execution_dir) if execution_dir is not None else source.parent
    try:
        NotebookClient(notebook, resources={"metadata": {"path": str(directory.resolve())}}, **kwargs).execute()
    except Exception as exc:
        raise RuntimeError(f'Execution failed for {source}: {exc}') from exc


def build(source: str | Path, *, output: str | Path = "build", prefix: str = "dev_", execute: bool = False,
          check: bool = False, source_roots: list[str | Path] | None = None,
          output_file: str | Path | None = None, suffix: str = '', overwrite: bool = True,
          clean_options: CleanOptions | None = None, timeout: int | None = None,
          kernel: str | None = None, execution_dir: str | Path | None = None, allow_errors: bool = False) -> Path:
    """Materialize one cleaned notebook, optionally executing or checking it."""
    if check and execute:
        raise ValueError("--execute cannot be combined with check")
    options = clean_options or CleanOptions()
    if execute and options.load_clean == 'keep':
        raise ValueError('--execute cannot be combined with --load-clean keep: retained magics could synchronize source files')
    if not execute and (timeout is not None or kernel is not None or execution_dir is not None or allow_errors):
        raise ValueError('Kernel, timeout, execution directory and allow-errors options require --execute')
    if timeout is not None and (timeout == 0 or timeout < -1):
        raise ValueError('Timeout must be a positive number of seconds or -1 for no limit')
    if execution_dir is not None and not Path(execution_dir).is_dir():
        raise ValueError(f'Execution directory does not exist: {execution_dir}')
    source_path = Path(source)
    if not source_path.is_file():
        raise ValueError(f"Source does not exist or is not a file: {source_path}; select an existing saved .ipynb or py:percent file")
    if source_roots is not None:
        source_roots = [Path(root).resolve() for root in source_roots]
        for root in source_roots:
            if not root.is_dir():
                raise ValueError(f"Source root is not a directory: {root}; select the directory containing your helper modules")
    target = Path(output_file) if output_file is not None else _target(source_path, output, prefix, suffix)
    _validate_tasks([(source_path, target)], overwrite=overwrite)
    try:
        notebook = clean_notebook(load_source_notebook(source_path), source_roots=source_roots, options=options)
    except (ValueError, RuntimeError, OSError, SyntaxError) as exc:
        raise ValueError(f"{source_path}: {exc}") from exc
    if execute:
        _execute(notebook, source_path, timeout=timeout, kernel=kernel, execution_dir=execution_dir, allow_errors=allow_errors)
    if options.clear_metadata:
        notebook.metadata = {}
        for cell in notebook.cells:
            cell.metadata = {}
    if check:
        return target
    nbformat = _dependency("nbformat")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, suffix=".ipynb", delete=False) as handle:
            temporary = Path(handle.name)
            nbformat.write(notebook, handle)
        if overwrite:
            os.replace(temporary, target)
        else:
            # Refuse even an output that appeared after preflight validation.
            os.link(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def build_default(*, source_dir: str | Path = "notebooks", output: str | Path = "build", prefix: str = "dev_",
                  execute: bool = False, check: bool = False, source_roots: list[str | Path] | None = None,
                  suffix: str = '', recursive: bool = False, include: list[str] | None = None,
                  exclude: list[str] | None = None, overwrite: bool = True, **kwargs) -> list[Path]:
    """Build prefixed notebooks, rejecting ambiguous pairs and collisions."""
    if check and execute:
        raise ValueError("--execute cannot be combined with check")
    tasks = plan_build([source_dir], output=output, prefix=prefix, suffix=suffix, recursive=recursive,
                       include=include, exclude=exclude, overwrite=overwrite)
    return [build(source, output_file=target, execute=execute, check=check, source_roots=source_roots,
                  overwrite=overwrite, **kwargs) for source, target in tasks]
