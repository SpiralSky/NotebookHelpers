# Experiment in notebooks, maintain code in files

Use notebooks for experiments and explanations, Python modules for reusable
functions, and tests for behavior you want to preserve. load-clean brings selected
module definitions into a notebook when you need an embedded export. It does not
currently save edited notebook definitions back into modules.

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
python -m jupytext --set-formats ipynb,py:percent dev_example.ipynb
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
python -m jupytext --sync dev_example.ipynb
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
paired representations: directory builds currently reject that ambiguity.

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

For a function prototyped in a notebook, copy its definition and required imports
into a module, replace the defining cell with an import, and put a stable example
into a test. This is currently a manual promotion step. For a new, small module,
IPython also supports:

```python
%%writefile scratch_helpers.py
def double(value):
    return value * 2
```

This writes the cell but does not execute its Python body. Run
`from scratch_helpers import double` in another cell to use it.
[`%%writefile`](https://ipython.readthedocs.io/en/stable/interactive/magics.html#cellmagic-writefile)
overwrites the entire destination; it does not merge functions. After promotion,
remove the writer cell or turn it into documentation so rerunning the notebook
cannot overwrite later module edits. Do not keep using two editable copies.

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
explicit; automatic save integration requires Jupytext in the Jupyter server
environment. Save/close before switching editors and synchronize before reopening.
If both copies have diverged, back up both and reconcile them before syncing;
timestamp selection is not a semantic merge. load-clean build reads the file
selected, without synchronizing the pair.

If notebook cells should remain the authoritative implementation of an entire
library, evaluate [nbdev](https://nbdev.fast.ai/tutorials/tutorial.html), which
exports designated cells to modules and integrates tests and documentation.
That is a different authoring model from promoting experiments into ordinary
modules; load-clean does not currently offer that package workflow.
