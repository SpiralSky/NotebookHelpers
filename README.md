# load-clean

Load selected Python definitions into notebooks and export notebooks without
`%%load_clean` cells. Python 3.10–3.14 is covered by CI.

This is a pre-1.0 project. Review generated code before sharing or executing it;
API stability and a maintenance or response-time SLA are not promised.

## Install

```sh
python -m pip install '.[notebook,tools]'
```

Run this from a source checkout. The core package needs no IPython installation.
The `notebook` extra adds IPython; `tools` adds notebook parsing, synchronization,
and execution dependencies. Contributors can use `python -m pip install -e '.[dev]'`.

## Quickstart

Given an importable `helpers.py` containing `def greet(name): return f"Hello {name}"`,
load the extension in an IPython notebook:

```python
%load_ext load_clean
```

Then run a cell:

```python
%%load_clean
from helpers import greet
```

The default mode executes the import. It does not embed source or execute the
rest of the cell as arbitrary Python. Use an optional final list to select names:

```python
%%load_clean inline
from helpers import greet
[greet]
```

`inline` embeds selected definitions and supported static local dependencies.
Unsupported dependencies raise errors instead of silently creating incomplete
exports. `skeleton` produces teaching stubs whose callable bodies raise
`NotImplementedError`; these stubs are not working implementations.

```sh
load-clean --help
load-clean-build --help
```

`load-clean` is the primary CLI. `load-clean-build` remains a compatibility alias.
See [usage and limitations](docs/usage.md), [migration](docs/migration.md), and
[support policy](docs/support.md).
