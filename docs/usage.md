# Usage and limits

For the complete experiment → module → Git → export journey, start with
[the workflow guide](workflow.md). This page is the command and API reference.

## Notebook modes

Load `%load_ext load_clean` once per IPython session. The cell magic accepts
`default`, `inline`, and `skeleton`; omitting a mode selects `default`.

```python
%%load_clean
from helpers import greet
```

Default mode executes the import and exports the import statement. Inline mode
embeds Python definitions instead:

```python
%%load_clean inline
from helpers import greet
[greet]
```

Use explicit `from module import symbol` imports for embedding. Wildcard imports
require an explicit final selection list, such as `[greet]`. The optional list
selects definitions; the cell body is not a general-purpose Python program.

Skeleton mode uses the same selection syntax but replaces callable bodies with
`raise NotImplementedError`. Use it for exercises and interface illustrations.

Inspect a selection before loading it:

```python
%load_clean_preview inline from helpers import greet
%load_clean_check inline from helpers import greet
%load_clean_materialize inline from helpers import greet
%load_clean_status
```

Preview renders the resolved source without executing the import or source.
Check validates a selection and reports its source SHA-256 without loading it.
Materialize places generated ordinary Python in a new input cell without
executing it. Status reports recorded hashes and whether source changed since
the last successful load; check without arguments also displays status. Line
commands select names through explicit from-imports and do not accept a final
selection list.
These operations do not prove that generated code is safe or semantically
identical under every runtime environment.

## Save a prototype as a module

```python
%%load_clean_save --preview helpers.py
# Source formatting and comments are preserved.
def double(value):
    return value * 2
```

Remove `--preview` to create a new file. Quote paths containing spaces.
Preview prints the resolved destination and exact cell body without writing,
creating directories, importing modules, or executing the body. Preview may
inspect a destination that already exists; creation always refuses it. Syntax is
validated in both modes, including rejection of non-UTF-8 encoding declarations.
A `.py` suffix and existing parent directory are required. Relative paths use the
kernel's working directory; `~` is expanded. Symlinks in the destination or any
parent component (including dangling destination links) are refused. Filesystem
parents must be trusted and remain stable during the operation.

Creation writes a temporary sibling, then publishes the complete file using an
atomic hard link that cannot overwrite a competing destination; the temporary
file is removed afterward. The filesystem must support hard links. A failed
validation, write, or publication preserves existing files. There is no overwrite
or replacement option: edit the authoritative module directly. The complete body
is saved as UTF-8 without newline or formatting normalization, and never executed.
Dependencies from kernel state are not extracted.

After saving, replace the writer cell with an import and add a behavior test.
No notebook cell is rewritten automatically. If retained temporarily, give the
writer cell the `load-clean-remove` tag, along with extension setup cells.
Build removes these cells before resolution. An untagged `%%load_clean_save`
cell is rejected by check/build with a removal/tagging instruction.

The report suggests `import module` only when standard filesystem path lookup
finds that exact file, including package and namespace-package layouts. Package
initializers are inspected by path without execution. Unsupported paths, invalid
module identifiers, and shadowed modules receive source-setup guidance instead.
Custom import hooks and already cached modules can affect runtime imports; use
a fresh kernel to verify. For a consumer project's `src/` layout, an editable
installation in the kernel environment (`python -m pip install -e .`) normally
provides the source path. Saving neither installs nor imports anything.

## Static resolution

Embedding reads local Python source and follows supported static dependencies.
Source lookup scans `sys.path` without importing parent packages. API callers
may pass `source_roots=[Path("src")]` to `resolve_cell` for exclusive, ordered
filesystem lookup. Resolution is
scope-aware, but Python's dynamic behavior cannot generally be determined from
source alone. Unsupported dependencies and constructs produce explicit errors;
resolve them before sharing an export.

AST rendering normalizes formatting and does not preserve source comments.
Embedding does not vendor third-party libraries or make a notebook independent
of all installed dependencies. Review imports and run the exported notebook in
the intended environment.

## Python API

Core source resolution does not require IPython:

```python
from load_clean.api import resolve_cell

source = resolve_cell("from helpers import greet", ["greet"], mode="inline")
```

The same mode semantics and strict embedding limits apply to API calls.
Whole-cell saving also has an IPython-independent API:

```python
from load_clean.api import save_cell

preview = save_cell("helpers.py", "answer = 42\n", preview=True)
result = save_cell("helpers.py", preview.source)
# result.path, result.source, result.import_line (None if setup is needed)
```

The API uses the same new-file, validation, and filesystem policy as the magic.

## Pair and synchronize saved notebooks

From a source checkout, install `python -m pip install -e '.[tools]'`, then
select one existing file explicitly:

```sh
load-clean pair --source "notebooks/dev_trial.ipynb"
load-clean sync --source "notebooks/dev_trial.py"
```

Pair creates a same-directory `.ipynb`/`py:percent` pair and records Jupytext
metadata. It accepts a notebook or a percent script (with `# %%` cell markers),
refuses ordinary modules/directories/other formats, and refuses an existing
counterpart. Sync requires the recorded `ipynb,py:percent` pairing; it can recreate
a missing counterpart. Other Jupytext pairing layouts are outside this wrapper's
scope; use Jupytext directly for those layouts.

Both commands use Jupytext and print each file's exact path with `created`,
`updated`, or `unchanged`, comparing content bytes. Jupytext can normalize metadata
or update timestamps even when cell inputs stay the same. Notebook outputs are
retained for matching cells under Jupytext's rules; edited/new cells may have no
matching output, and retained outputs do not prove results are current. Sync does
not execute code.

Sync takes inputs from the most recently modified saved representation and
outputs from the notebook. Passing `--source` chooses the pair, not a winning
side. This is not semantic merging or reliable divergent-edit detection. Save and
close editors first: unsaved edits are inaccessible. If both copies were edited,
back up and reconcile them before syncing. For deliberate one-file export,
`load-clean build --source "notebooks/dev_trial.py"` (or the `.ipynb`) reads exactly
that file without syncing. To re-pair from one chosen copy, back up both elsewhere,
remove its counterpart, and pair the retained file. No directory-wide sync exists.

## Build and inspect notebooks

From a source checkout, install `python -m pip install -e '.[tools]'` before
using notebook commands. Add `ipykernel` for execution in this environment.

```sh
load-clean build --source notebooks --output build --prefix dev_
load-clean check --source notebooks --output build
load-clean doctor
```

`--source` accepts a file or directory. Check resolves and validates without
writing output; `build --check` is an equivalent spelling. Doctor reports the
environment and optional dependencies. Legacy invocations such as
`load-clean-build --source notebooks --output build` remain supported.

Build writes outputs atomically and rejects input overwrites, output name
collisions, and ambiguous paired sources in directory input. The default source
and output directories are `notebooks` and `build`.

```sh
load-clean build --source notebooks --output build --execute
```

Execution is opt-in and uses nbclient. It runs notebook code with the privileges
of the current process; use trusted inputs and a suitable kernel environment.
Execution cannot be combined with check mode. A successful static check alone
does not establish that a notebook executes successfully.

Both check spellings keep proposed paths on stdout; their success message on
stderr explicitly says no code executed and no output was written. Build keeps
written paths on stdout and identifies source and destination on stderr. Static
check success does not test runtime imports, assertions, or other cell behavior.

For helpers that are not installed, select source roots explicitly:

```sh
cd examples
load-clean check --source dev_example.ipynb --source-root . --output ../build
load-clean build --source dev_example.ipynb --source-root . --output ../build --execute
```

`--source-root` is repeatable. Roots are relative to the terminal's working
directory, must be existing directories, and replace `sys.path` lookup for static
embedding; the first matching source wins. Specify only intended project roots
in the desired order. No notebook-directory root is added implicitly and no
helper or parent initializer is imported. This avoids depending on executable
versus `python -m` path differences or accidentally adding local shadow modules.
Without the option, existing `sys.path` lookup remains. This setting never edits
`sys.path`, installs packages, or changes fresh-kernel runtime imports. Install
the helper project separately when retaining ordinary imports in an export.

Inline loads read current on-disk definitions into a snapshot. Edit/save the
module, rerun the inline cell, then rerun dependent calculations. Ordinary
imports use Python's normal module cache; reload the module explicitly or use
IPython autoreload and rerun consumers. `%load_clean_status` detects file changes
against recorded fingerprints but cannot certify that downstream results are
fresh, even when it reports unchanged. Nothing automatically reruns cells.
