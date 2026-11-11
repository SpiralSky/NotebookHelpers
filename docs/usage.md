# Usage and limits

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

## Static resolution

Embedding reads local Python source and follows supported static dependencies.
Source lookup scans `sys.path` without importing parent packages. Resolution is
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

## Build and inspect notebooks

Install the `tools` extra before using notebook commands.

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
