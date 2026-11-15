# Migration from the initial prototype

## Sync-on-run workflow

The primary interface is now `%%load_clean path.py` with the complete module body,
or `%load_clean path.py` to open an existing module without execution. Keep the
generated `--base` header. Each Run synchronizes the changed side; conflicting
edits error before writing or executing. See [linked-cell semantics](usage.md#linked-cells-primary-interface).
The previous import-selection and creation-only save commands remain compatible.
Do not convert a selected function cell into a whole-file link over a larger module;
load the complete module first. No frontend plugin or background watcher is installed.

## Earlier compatibility changes

Install `.[notebook]` for the IPython extension and `.[tools]` for notebook build
commands. IPython and pytest are no longer core runtime dependencies. Development
and testing dependencies are available with `.[dev]`.

Use `load-clean` for new scripts. The existing `load-clean-build` executable
continues to dispatch to the same CLI, and legacy build flags remain supported.
Check `load-clean --help` for the complete command interface.

Default mode now preserves the import alone. Select `inline` explicitly when an
export must contain Python definitions. Inline resolution rejects unsupported
constructs and dependencies rather than generating a best-effort incomplete
notebook. Review and fix these errors before distributing an export.

Skeleton callable bodies raise `NotImplementedError` so accidental execution
fails clearly. They are exercises or interface illustrations, not usable copies
of the source implementation.

Pre-1.0 interfaces may change. Pin the exact version for reproducible workflows
and inspect generated notebook changes when upgrading.
