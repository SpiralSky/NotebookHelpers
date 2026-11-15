# Edit, run, and synchronize

Use your notebook editor with an IPython kernel. Install load-clean in that kernel
with `python -m pip install -e /path/to/NotebookHelpers[notebook,tools] ipykernel`
(quote the path and extras in shells that expand brackets). The project does not
require JupyterLab; frontend support for cell insertion/replacement varies.

## Start from an import

Run this setup cell once and tag it `load-clean-remove` for export:

```python
%load_ext load_clean
```

Suppose your project has `helpers.py` containing:

```python
import math

def magnitude(x, y):
    return math.sqrt(x * x + y * y)
```

Select that function in a notebook cell:

```python
%%load_clean
from helpers import magnitude
```

Run once. The module executes and the tool requests an editable replacement cell
containing the import statement, a separate `# Referenced Source: sha256:...`
baseline comment, and the function source. Keep the import and comment.
The import determines the destination; edit the function and run again:
changes synchronize to its definition in the file, preserving the `math` import
and unrelated definitions. The function runs with the module's globals and package
context. Aliases and multiple names work, for example
`from helpers import magnitude as norm, another_function`.

Use `import helpers` instead to link the complete module; calculations then use
`helpers.magnitude(...)`. Imports use the kernel environment's filesystem module
paths. For a `src/` project, make the package importable in that environment.

Successful sync adds no cell output; module code can still print or display.
If your editor ignores replacement requests, preserve edits and reload using a
frontend that supports replacement before continuing. Put temporary computations in separate cells:

```python
assert magnitude(3, 4) == 5
magnitude(5, 12)
```

Selected cells may edit directly defined functions, classes, or simple assignments.
Keep the selected names intact; edit module-level imports and other shared dependencies
in the source file or a whole-module link. Re-exports and ambiguous definitions
raise errors instead of guessing a write target. See [limits](usage.md).

For a new module that cannot yet be imported, the path form remains available:

```python
%%load_clean new_helpers.py
def double(value):
    return value * 2
```

Path links own the whole file and execute in the notebook namespace. The line form
`%load_clean path.py` opens an existing whole file without executing it; tag or
remove that one-time loader cell before exporting. Import-addressed cells above
are the primary interface for existing modules and selected functions.

## Edit on either side

Edit the linked cell and press Run: it validates, writes the file, and executes.
Edit the file instead and press Run on the unchanged cell: it requests a refreshed
cell and executes the file version. Import links keep their baseline in the
reference comment; path links keep it in the header. Save the notebook to retain
the baseline across restarts. No fallback source is displayed.

No background synchronization occurs. Ordinary notebook Save only saves the
notebook, and ordinary file Save only saves the module. Running the linked cell
is the synchronization point. A runtime failure leaves a successful sync saved;
invalid syntax prevents a write. Status and execution success are distinct.

If both copies changed the selected source differently, Run reports a conflict and a diff.
Unrelated file edits are preserved when saving selected definitions. Neither
copy is written and no cell code executes. Preserve both copies, reconcile them,
and make their contents identical before running again. Alternatively load the
file into a new cell and manually transfer edits. Do not delete or change the hash
to force an overwrite. Git commits help you review and recover committed versions;
they do not protect every uncommitted edit.

The editor update is a request, not an acknowledged hook. If your editor ignores
it, the cell stays stale and there is no automatic source display as a fallback.
Preserve edits and reload using a frontend that supports replacement.
There is no automatic merge and no background file watcher. Avoid saving from two
editors during the same run; the final byte comparison and atomic write are not a
filesystem compare-and-swap. Detailed limits are in [the reference](usage.md).

Import-linked code re-executes the synchronized module with its package context.
Its top-level effects run on each execution. Dependencies imported by that module
retain normal Python caching; existing external function references and previously
computed notebook results remain unchanged until refreshed.
Restart and run the notebook to check that it does not depend on stale kernel state.

## Export

Run linked cells, save the notebook as `dev_analysis.ipynb`, then:

```sh
load-clean check --source dev_analysis.ipynb --output build
load-clean build --source dev_analysis.ipynb --output build --execute
```

The output is `build/analysis.ipynb`. Import-linked cells become their original
ordinary import statements. Their project modules must remain importable in the
recipient's environment. A cell with unsynchronized edits blocks export: run it
and save first. Build does not read linked source files or certify their version,
and an executed build uses the modules available in its fresh kernel.

Explicit path links instead export their saved notebook bodies as ordinary Python.
Neither form synchronizes source files during build/check. Tag the extension setup
cell `load-clean-remove`. Generated exports may replace previous outputs; source
notebooks are preserved. Other libraries, data files, and imported modules remain
runtime dependencies. Ordinary Python can have side effects; export removes the
synchronization operation only.

Use explicit `%%load_clean inline` with a from-import when you need supported
selected source and dependencies embedded in the notebook. This export mechanism
is separate from editable links and has stricter dependency limits; see [usage](usage.md).

## Git and notebook pairing

Track modules, tests, and the notebook representation your project needs. Keep
`.venv/` and generated `build/` output out of Git. Review `git diff` before committing.
New files appear in `git status`; read them before staging.

Optionally create a Git-friendly percent-format notebook:

```sh
load-clean pair --source dev_analysis.ipynb
load-clean sync --source dev_analysis.ipynb
```

These CLI commands synchronize the notebook and its text representation via
Jupytext. They are separate from linked-cell/module synchronization. Save and
close editors before switching representations. Jupytext uses saved-file recency,
not a three-way merge; selecting a source path does not force that side to win.
If both representations were edited, back up and reconcile them before syncing.
Pair refuses an existing counterpart, and directory builds reject ambiguous
pairs. Always select the intended saved notebook file explicitly for export.
