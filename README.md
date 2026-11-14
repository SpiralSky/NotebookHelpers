# load-clean

Experiment in notebooks, keep reusable Python in files, and embed selected
helpers when exporting notebooks. Python 3.10–3.14 is covered by CI.

Use ordinary imports for development, Jupytext for Git-friendly notebook text,
and load-clean for selected source embedding and clean notebook delivery.
Saving notebook functions back into modules is currently a manual step.

## Start here

From a source checkout, in the environment used by your notebook kernel:

```sh
python -m pip install -e '.[notebook,tools]' ipykernel
cd examples
python -m load_clean_tools.cli build --source dev_example.ipynb --output ../build --execute
```

This writes `build/example.ipynb` at the repository root and runs its assertion
and greeting in a fresh kernel. Run from `examples` so the helper module can be
found. Omit `--execute` to build without executing code. The original notebook
is preserved; an existing generated output is replaced.

Follow [the notebook-to-files workflow](docs/workflow.md) for interactive setup,
rapid iteration, saving prototypes into modules, text pairing, Git review, and
project layout. A notebook frontend is installed separately; the `notebook`
extra supplies IPython, not JupyterLab.

## Choose an export mode

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

The magic body accepts imports and an optional final selection list, not arbitrary
Python experiments. Embedding does not vendor every dependency and rejects
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
