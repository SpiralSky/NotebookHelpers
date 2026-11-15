# Usage and limits

For the complete experiment → module → Git → export journey, start with
[the workflow guide](workflow.md). This page is the command and API reference.

## Linked cells: primary interface

Load `%load_ext load_clean` once, then use a normal import:

```python
%%load_clean
from my_project.helpers import double as twice
```

`import my_project.helpers as helpers` links the entire module. A `from` import
links the selected top-level definitions; multiple explicit names are supported.
On the first run, the source is loaded, an editable replacement cell is requested,
and the complete module executes with its package context. The requested names
are bound in the notebook with normal alias semantics. Subsequent runs synchronize
first and re-execute the module snapshot, bypassing stale bytecode caches.
Relative imports inside that module, `__file__`, and module globals work. Top-level
effects run each time; dependencies imported by the module retain normal caching.
Old external `from` bindings and previously computed results are not refreshed.

The generated header carries `--import`, `--file`, and `--base`. Keep all three.
The file is pinned and the baseline hashes only the selected source. Unrelated
file edits can coexist with a selected-definition edit: the current file supplies
the surrounding source and only selected spans are replaced. Different edits to
the selected region conflict. AST is used to locate/validate spans, not regenerate
the module. Unselected text and comments are preserved, including CRLF and BOM.

Editable selections support directly defined top-level functions (including async
and decorators), classes, and simple single-name assignments. Re-exports, conditional
definitions, repeated bindings, wildcard imports, and definitions sharing a line
are refused. Keep original definition names even when importing with aliases.
Put comments inside the selected definitions; additional standalone comments or
imports in a selected cell are rejected rather than silently discarded. Edit shared
module imports/globals in the file or use a whole-module link. Renaming or adding
definitions requires a whole-module link or a source-file edit.

Source lookup uses standard filesystem module/package precedence without running
package initializers. Custom meta-path import hooks, compiled modules and source
inside archives are not editable links. If imports resolve elsewhere or a cached
module points elsewhere, linking stops. Package initializers run as needed during
execution, just as with imports. Runtime errors leave successful file syncs saved.

Import-linked export emits the original import, not an isolated function body:
this preserves dependency and package semantics. Export requires the cell body to
match its baseline but does not inspect the source file, so it does not certify
that file is unchanged. The project must be importable at runtime; use explicit
`inline` mode for selective embedding. Neither check nor build syncs import links.

## Explicit whole-file path links

Load `%load_ext load_clean` once. `%load_clean path.py` reads a complete existing
UTF-8 module and requests a new linked cell, without execution. Alternatively,
`%%load_clean path.py` with a Python body creates a new file and executes it.
Quote paths containing spaces. Parent directories must exist; symlink files and
parents are refused. A cell represents the whole file, not one selected function.

The generated header is `%%load_clean /absolute/path.py --base SHA256`. Keep it:
the digest records the last synchronized source and survives kernel restarts
when the notebook is saved. There is no hidden per-kernel baseline or Git commit
requirement. Line endings and trailing newlines are normalized for comparison;
comments, internal whitespace, and other source text are preserved. A differing
existing file cannot be overwritten by a cell without a baseline.

On each Run:

| Cell vs baseline | File vs baseline | Result |
| --- | --- | --- |
| Unchanged | Unchanged | Execute cell |
| Changed | Unchanged | Validate, save file, execute |
| Unchanged | Changed | Validate, request refreshed cell, display source, execute file version |
| Changed | Same content as cell | Mark in sync, execute |
| Changed | Differently changed | Error with file/cell diff; no write or execution |

Syntax is checked before writing. A runtime exception does not undo a successful
sync; status is printed before execution. All code in the linked cell belongs to
the module, including imports and top-level effects. Put temporary experiments
and assertions in separate cells. Other imported module objects, old function
references, and previous notebook results are not automatically refreshed.

IPython's `set_next_input` requests insertion/replacement. No frontend acknowledgment
is available and no GUI integration is shipped. If the request is ignored, copy
the displayed linked cell (including its updated baseline) before editing. The
updated source is displayed when the baseline changes; stale headers cause safe
conflicts rather than implicit overwrite. Loading does not execute; a file-only
update on Run executes the displayed updated source even if replacement is ignored.

Resolve conflicts by preserving both copies, reconciling their contents, and
making the cell and file identical before running again. Or load the file into
a new cell with `%load_clean path.py` and transfer intended edits manually.
Deletion is an error, not an instruction to recreate a previously linked file.

Updates use a temporary sibling and atomic replacement, preserve permission bits,
and recheck file bytes just before replacement. This detects edits during staging
but is not a filesystem compare-and-swap: an external writer in the final interval
can still race. Avoid simultaneous saves while running. Hard-linked aliases are
not updated by replacement; extended attributes/ACLs are not preserved. Parents
must be trusted and stable. Git cannot restore arbitrary overwritten uncommitted
work, so it does not replace these checks.

Build/check strip a linked header and validate the saved cell body without reading
or writing its linked file. Even an executed build cannot synchronize that file.
Remove or tag standalone `%load_clean path.py` loader cells `load-clean-remove`;
export rejects them and retains the generated linked code cells instead.
This exports a notebook snapshot, not necessarily the latest on-disk module: run
and save the notebook before exporting. Existing selective embedding below remains
available, but AST regeneration is not used for linked-file synchronization.

Execution uses the notebook namespace, not an imported module namespace. Code
depending on package-relative imports, module `__file__`, or package initialization
may require adaptation; use ordinary imports for such modules. Modules with
top-level effects run those effects on every linked-cell execution.

## Legacy import-selection modes

For the older import-selection syntax, the cell magic accepts explicit `default`,
`inline`, and `skeleton`. A bare header now creates an editable import link.

```python
%%load_clean default
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

This older creation-only command remains available for compatibility. Prefer
linked cells above for automatic sync and execution on Run.

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
