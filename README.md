# load-clean

Edit Python in a notebook or a file, then synchronize when you run the linked
cell. Conflicting edits stop with a diff instead of overwriting either copy.
Python 3.10–3.14 is covered by the CI configuration.

## Start here

From a source checkout, in the environment used by your notebook kernel:

```sh
python -m pip install -e '.[notebook,tools]' ipykernel
```

For an existing module, make it importable in the kernel environment. For this
example, save `helpers.py` beside the notebook with:

```python
def double(value):
    return value * 2
```

Run `%load_ext load_clean` in a separate setup cell, then select the code using
a normal import in another cell:

```python
%%load_clean
from helpers import double
```

This runs the module and replaces the request with an editable linked definition.
Use `import helpers` to link the entire module, or
`from helpers import double as twice` for an alias. Multiple explicit selected
names are supported. Module-relative imports and globals retain their package context.

The generated cell keeps the import immediately below the magic, then a separate
`# Referenced Source: sha256:...` comment and the editable source. Keep the import
and reference comment, then edit/run normally. The comment records the last
synchronized source, not a Git commit; save the notebook to retain it across
kernel restarts. The import determines the destination on each Run. Cell-only
edits save to the file; file-only edits refresh the cell and run the new source;
different edits on both sides produce an error before writing or executing.
Run your tests or calculations in separate cells, for example `double(21)`.

Selected-definition edits preserve the rest of the file. Edit module-level imports
and shared dependencies in the file, or link the whole module. Re-exports and
ambiguous definitions are rejected rather than guessed.

For a **new file**, the explicit path form remains available:

```python
%%load_clean helpers.py
def double(value):
    return value * 2
```

Path links own the complete file and execute in the notebook namespace. To load
an existing whole file without execution, use `%load_clean helpers.py`; remove or
tag that one-time loader cell `load-clean-remove` before export.

Cell insertion/replacement uses IPython editor requests, not a JupyterLab plugin.
Successful load/sync operations produce no status messages or source displays;
output from your own module code still appears. If your frontend ignores editor
requests, the cell will not refresh: preserve edits and reload in a frontend
that supports replacement before continuing. There is no background file watcher.

Follow [the workflow guide](docs/workflow.md) for conflicts, export, and Git review.
A notebook frontend is installed separately; the `notebook`
extra supplies IPython, not JupyterLab.

## Export and compatibility

To try an export immediately, run these commands from the checkout root after
installing the dependencies above:

```sh
load-clean check examples/dev_example.ipynb --source-root examples
load-clean build examples/dev_example.ipynb --source-root examples --execute
```

Check validates without writing or executing. Build creates `build/example.ipynb`
and executes it in a fresh kernel; its final output is `Hello, world!`. This
checked-in example uses `inline` to embed the helper function. The explicit source
root locates it for static resolution without installing the example helper.

Tag the extension setup cell `load-clean-remove`, save `dev_analysis.ipynb`, then:

```sh
load-clean build --source dev_analysis.ipynb --output build --execute
```

Import-linked cells export the original import, so the project must be installed
or importable when the export runs. Unsynchronized cell edits block export. Path
links export the notebook body as ordinary Python. Export does not sync files:
run the linked cells and save the notebook first. The output is
`build/analysis.ipynb`; source inputs are preserved, generated outputs replaced.

Build policies are configurable without changing notebook syntax:

```sh
# Remove only load-clean headers, retaining their Python bodies and imports.
load-clean build dev_analysis.ipynb -o deliverables --load-clean strip --strip-setup

# Preview recursive selection and output paths without writing anything.
load-clean build notebooks -r --include '*.ipynb' --exclude 'scratch/*' -o deliverables -n

# Choose an exact output file and refuse overwriting an existing one.
load-clean build dev_analysis.ipynb -O deliverables/report.ipynb --no-clobber
```

`--load-clean resolve|strip|remove|keep` controls magic handling. Imports remain
unless `--imports remove-cells` explicitly drops import-only cells. Output state,
tags, metadata, execution settings and reporting have separate controls. Run
`load-clean build --help` or read [the build reference](docs/usage.md#build-and-inspect-notebooks).
Removing imports or stripping a selected-definition header does not automatically
supply that code's dependencies.

The older import-selection interface remains available for selective embedding:

Load `%load_ext load_clean` once in your notebook, then run:

```python
%%load_clean inline
from example_helpers import greet
```

| Mode | Result |
| --- | --- |
| `default` (explicit) | Execute and preserve an ordinary import without linking |
| `inline` | Embed selected definitions and supported static local dependencies |
| `skeleton` | Create exercise stubs that raise `NotImplementedError` |

These legacy import-selection forms accept imports and an optional final selection
list. Path-based linked cells accept a complete Python module instead.
Selective embedding does not vendor every dependency and rejects
unsupported constructs. Use ordinary imports when embedding is unnecessary.

## Reference and development

- [Command and API reference, modes, and limits](docs/usage.md)
- [Migration](docs/migration.md) and [support policy](docs/support.md)
- [Project direction and prioritized UX work](docs/APPROACH.md)

`load-clean` is the primary CLI; `load-clean-build` remains a compatibility alias.
Use `load-clean --help` to see commands. Core source resolution needs no IPython;
`tools` adds notebook parsing, pairing, and execution dependencies. Contributors
can install `python -m pip install -e '.[dev]'`.

This is a pre-1.0 project. Review generated code before sharing or executing it;
API stability and a maintenance or response-time SLA are not promised.
