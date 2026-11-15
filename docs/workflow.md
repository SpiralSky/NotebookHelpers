# Edit, run, and synchronize

Use your notebook editor with an IPython kernel. Install load-clean in that kernel
with `python -m pip install -e /path/to/NotebookHelpers[notebook,tools] ipykernel`
(quote the path and extras in shells that expand brackets). The project does not
require JupyterLab; frontend support for cell insertion/replacement varies.

## Start a linked module

Run this setup cell once and tag it `load-clean-remove` for export:

```python
%load_ext load_clean
```

Create a new file from a complete module cell:

```python
%%load_clean helpers.py
import math

def magnitude(x, y):
    return math.sqrt(x * x + y * y)
```

Running creates the file, executes the body, and requests an updated header with
an absolute path and baseline hash. Keep that header unchanged. For an existing
module, run `%load_clean helpers.py` instead: it loads the complete source into a
new linked cell without executing it. If the editor does not insert/replace cells,
copy the displayed cell including its header. A differing existing file is never
silently adopted by a new cell without a baseline.
Remove the one-time `%load_clean` loader cell or tag it `load-clean-remove`; keep
the generated linked code cell. Export rejects an untagged loader cell.

One cell owns the whole module, including imports and comments. This version does
not synchronize a single function inside a larger module. Use small helper modules
when you want small editable cells. Put temporary computations in separate cells:

```python
assert magnitude(3, 4) == 5
magnitude(5, 12)
```

## Edit on either side

Edit the linked cell and press Run: it validates, writes the file, and executes.
Edit the file instead and press Run on the unchanged cell: it requests a refreshed
cell, displays the updated source, and executes the file version. The baseline
lives in the header, so save the notebook to retain it across restarts.

No background synchronization occurs. Ordinary notebook Save only saves the
notebook, and ordinary file Save only saves the module. Running the linked cell
is the synchronization point. A runtime failure leaves a successful sync saved;
invalid syntax prevents a write. Status and execution success are distinct.

If both copies changed differently, Run reports a conflict and a diff. Neither
copy is written and no cell code executes. Preserve both copies, reconcile them,
and make their contents identical before running again. Alternatively load the
file into a new cell and manually transfer edits. Do not delete or change the hash
to force an overwrite. Git commits help you review and recover committed versions;
they do not protect every uncommitted edit.

The editor update is a request, not an acknowledged hook. If your editor ignores
it, the displayed refreshed cell is the fallback; copy it before editing further.
There is no automatic merge and no background file watcher. Avoid saving from two
editors during the same run; the final byte comparison and atomic write are not a
filesystem compare-and-swap. Detailed limits are in [the reference](usage.md).

Functions execute in the notebook namespace. Separate `import helpers` consumers
still obey normal Python caching; they are not automatically reloaded. Previously
computed notebook results also remain unchanged until their cells run again.
Restart and run the notebook to check that it does not depend on stale kernel state.

## Export a snapshot

Run linked cells, save the notebook as `dev_analysis.ipynb`, then:

```sh
load-clean check --source dev_analysis.ipynb --output build
load-clean build --source dev_analysis.ipynb --output build --execute
```

The output is `build/analysis.ipynb`. Linked headers become ordinary Python bodies;
imports remain inside the cells. Build does not read or synchronize linked files,
so exports work after those files are moved or removed. Export uses the saved
notebook snapshot, not unseen edits in the editor or the newest module on disk.
The extension setup cell must be tagged `load-clean-remove`. Generated exports
can replace prior outputs, but source notebooks are preserved.

Recipients do not need load-clean for these cells. They still need third-party
libraries, data files, and any modules imported by the bodies. Running ordinary
Python can have side effects; export removes the synchronization action only.

For selected definitions from a larger module, the older explicit
`%%load_clean inline` import-selection interface remains available. That is an
export snapshot mechanism, not a linked function editor. See [usage](usage.md).

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
