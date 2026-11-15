# load-clean

Edit Python in a notebook or a file, then synchronize when you run the linked
cell. Conflicting edits stop with a diff instead of overwriting either copy.
Python 3.10–3.14 is covered by the CI configuration.

## Start here

From a source checkout, in the environment used by your notebook kernel:

```sh
python -m pip install -e '.[notebook,tools]' ipykernel
```

Run `%load_ext load_clean` once, then create a new linked file with:

```python
%%load_clean helpers.py
def double(value):
    return value * 2
```

Or open an existing file with `%load_clean helpers.py`. It requests a new editable
cell without executing the file. Remove or tag that one-time loader cell
`load-clean-remove` before exporting. One cell owns the **complete file**, including
imports; do not use a partial function copy to link an existing larger module.

Keep the generated header (including `--base`) and edit/run normally. Cell-only
edits save to the file; file-only edits refresh the cell and run the new source;
different edits on both sides produce an error before writing or executing.
Run your tests or calculations in separate cells, for example `double(21)`.

Cell insertion/replacement uses IPython editor requests, not a JupyterLab plugin.
If your frontend ignores them, copy the displayed updated cell, including its
header, before editing further. There is no background file watcher.

Follow [the workflow guide](docs/workflow.md) for conflicts, export, and Git review.
A notebook frontend is installed separately; the `notebook`
extra supplies IPython, not JupyterLab.

## Export and compatibility

Tag the extension setup cell `load-clean-remove`, save `dev_analysis.ipynb`, then:

```sh
load-clean build --source dev_analysis.ipynb --output build --execute
```

Linked cells export their saved notebook body as ordinary Python. Export does
not sync files: run the linked cells and save the notebook first. The output is
`build/analysis.ipynb`; source inputs are preserved, generated outputs replaced.

The older import-selection interface remains available for selective embedding:

Load `%load_ext load_clean` once in your notebook, then run:

```python
%%load_clean inline
from example_helpers import greet
```

| Mode | Result |
| --- | --- |
| `default` (or no mode) | Execute and preserve an ordinary import |
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
