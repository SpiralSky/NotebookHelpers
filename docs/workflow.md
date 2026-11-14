# Experiment in notebooks, maintain code in files

Use notebooks for experiments and explanations, Python modules for reusable
functions, and tests for behavior you want to preserve. load-clean brings selected
module definitions into a notebook when you need an embedded export. Use its whole-cell save action to promote a prototype into a new module;
after promotion, edit the module directly.

## Choose what you want to save

| Goal | Use | Source of truth |
| --- | --- | --- |
| Review notebook cells in Git | Jupytext `py:percent` pairing | Synchronize the pair before reviewing; edit one representation at a time |
| Reuse and test functions across notebooks | Ordinary `.py` modules with imports and IPython autoreload | The module after promoting a prototype |
| Deliver a notebook with selected helper source included | load-clean `inline` and build | Modules and development notebook; the build is generated |
| Author an entire package in notebooks | Consider nbdev | Notebook export cells; generated modules are outputs |

A text notebook is still a notebook: it can contain experiments, magics, and
side effects. Pairing it does not turn it into an importable library.

## Try the existing example

From this repository's root, install into the Python environment you will also
use for the notebook kernel:

```sh
python -m pip install -e '.[notebook,tools]' ipykernel
cd examples
python -m load_clean_tools.cli pair --source dev_example.ipynb
```

This creates `dev_example.py` beside the notebook and records the pairing.
Open `examples/dev_example.ipynb` in your existing notebook frontend, select that
Python environment, and insert this setup cell before the existing cells:

```python
%load_ext load_clean
```

Give the setup cell the `load-clean-remove` tag so it is excluded from exports.
Run the notebook: the final cell should print `Hello, world!`. If the helper
cannot be found, check `%pwd`: this example expects the kernel's working directory
to be `examples`. The extension must be installed in the selected kernel, not
only in the terminal's Python environment. A Jupyter frontend is not included
in the package extras.

Save and close the notebook before synchronizing from a terminal. From `examples`:

```sh
python -m load_clean_tools.cli sync --source dev_example.ipynb
python -m load_clean_tools.cli check --source dev_example.py --output ../build
python -m load_clean_tools.cli build --source dev_example.py --output ../build --execute
```

The check prints the proposed output path but writes nothing. Build produces
`build/example.ipynb` at the repository root, executes it in a fresh kernel,
and retains the new outputs. Without `--execute`, build clears outputs and does
not execute cells. The original notebook is preserved; an existing build target
is replaced. The export contains `greet` as ordinary Python and no load-clean
cell magic. The `python -m` invocation makes the current directory available for resolving
this uninstalled helper module; the installed `load-clean` entry point does not
necessarily include it. For an installed helper package, either invocation works.
Always select one file explicitly when a directory contains both
paired representations: directory builds reject that ambiguity and print both
valid explicit file commands. They never synchronize or select a side for you.

## Iterate on reusable code

For daily development, ordinary imports avoid maintaining a second function
body in the notebook. In a development-only cell tagged `load-clean-remove`:

```python
%load_ext autoreload
%autoreload 2
```

Use this in an ordinary cell:

```python
import example_helpers
assert example_helpers.greet("world") == "Hello, world!"
```

Edit and save `example_helpers.py`, then rerun the calling cell to try the change.
[Autoreload](https://ipython.readthedocs.io/en/stable/config/extensions/autoreload.html)
refreshes imports before cell execution, but has limitations around changed class
structure and extension modules. Restart and run all cells before accepting a
result; reloading does not rerun earlier computations or refresh old results.

For a function prototyped in a notebook, first preview its complete module
source (include required imports and globals). The parent directory must exist:

```python
%%load_clean_save --preview scratch_helpers.py
# Keep this comment in the module.
def double(value):
    return value * 2
```

Preview prints the absolute destination and exact source without writing or
executing anything. Remove `--preview` and run the cell to create the file.
Existing files are refused, including files created by a competing writer.
The body is saved exactly as UTF-8, with Python syntax checked first; it is not
executed. This saves the entire cell, without merging or capturing kernel state.

**Transfer ownership to the module:** replace the writer/definition cell with
`from scratch_helpers import double`, then add a test such as
`assert double(4) == 8` in your test suite. Edit `scratch_helpers.py` from then on.
The magic leaves the existing notebook cell unchanged. If you temporarily keep
it for reference, tag it `load-clean-remove`; a default rerun refuses to overwrite
later edits. There is no replacement option. An untagged save cell blocks export
with instructions to remove or tag it, so exported notebooks cannot accidentally
write a module. Tag the extension setup cell too.

For delivery, replace the ordinary import with `%%load_clean inline` plus
`from scratch_helpers import double`, as in the supplied example. Save the
notebook, synchronize any pair, then check/build the selected file. Build removes
tagged writer/setup cells before resolving imports and clears prior outputs;
`--execute` verifies the result in a fresh kernel. Keep the stable test in the
module's test suite independently of the notebook.

The save report suggests an import for ordinary filesystem layouts already on
Python's source path, including packages. For `src/my_project` layouts, install
the consumer project with `python -m pip install -e .` into the kernel environment
before importing. Saving never runs that setup or the suggested import. See
[the reference](usage.md#save-a-prototype-as-a-module) for path and safety limits.

Use `inline` when preparing an export, as in the supplied example. It reads
supported source from disk when its cell is run or the notebook is built; it does
not track later edits automatically. Rerun the inline cell and dependent cells
after editing the module. Preview/check are available in [the reference](usage.md).
Embedding does not include every third-party dependency or support all Python
constructs. Ordinary imports remain the fallback for unsupported code.

## Review and organize work

A growing consumer project can use this layout:

```text
pyproject.toml
src/my_project/          # reusable modules; install with pip install -e .
notebooks/dev_trial.py  # text notebook tracked in Git
notebooks/dev_trial.ipynb  # local outputs, or tracked if your team needs them
tests/                  # repeatable checks independent of notebook state
build/                  # generated delivery notebooks
```

Use an installed package once helpers live outside the notebook directory rather
than adding ad hoc `sys.path` edits to each notebook. Keep `build/` out of Git.
For the small example, review the paired text and helper with:

```sh
git diff -- dev_example.py example_helpers.py
git status --short
```

A new file appears in status but not in an unstaged `git diff`; open it before
staging. Teams can track only the text notebook and keep `.ipynb` outputs locally,
or track both deliberately. Do not blanket-ignore existing notebooks without
checking whether their outputs are part of the deliverable.

[Jupytext pairing](https://jupytext.org/using/paired-notebooks/) preserves outputs
in `.ipynb` and uses the newer representation for inputs. CLI synchronization is
explicit through `load-clean sync --source saved-file.ipynb` (or its paired `.py`);
selecting that path does not force it to win over a newer counterpart. Pair and
sync print `created`, `updated`, or `unchanged` for each exact file, comparing
content bytes; Jupytext may also adjust timestamps. Ordinary helper modules and
directories are refused. Automatic save integration requires Jupytext in the Jupyter server
environment. Save/close before switching editors and synchronize before reopening.
The CLI sees saved disk files and cannot access unsaved editor changes. It does
not track edit history or detect divergent edits reliably. If both copies were
edited, back up both and reconcile them before syncing; timestamp selection is
not a semantic merge. To export the intended saved input without syncing, use
`load-clean build --source dev_example.ipynb` or
`load-clean build --source dev_example.py`. To make one copy authoritative for
future pairing, back up both outside the pair directory, remove the unwanted
counterpart, then run `load-clean pair --source` on the retained file. Review the
new pair before reopening an editor. Pair refuses an existing counterpart.

If notebook cells should remain the authoritative implementation of an entire
library, evaluate [nbdev](https://nbdev.fast.ai/tutorials/tutorial.html), which
exports designated cells to modules and integrates tests and documentation.
That is a different authoring model from promoting experiments into ordinary
modules; load-clean does not currently offer that package workflow.
