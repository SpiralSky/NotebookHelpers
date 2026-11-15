# Migration from the initial prototype

## Sync-on-run workflow

The primary interface is now a bare `%%load_clean` with `import module` or
`from module import name`. The first run loads an editable whole-module or
selected-definition link and executes in module context. Keep the generated
`--import`, `--file` and `--base` header. Each Run synchronizes the changed side;
conflicting edits to the selected source error before writing or executing.
See [linked-cell semantics](usage.md#linked-cells-primary-interface).

Bare imports previously performed an ordinary import without creating a link.
Use explicit `%%load_clean default` to retain that behavior. `inline`, `skeleton`,
creation-only save, and whole-file path links remain available. Import links
export the original import and require the project at runtime; they do not export
isolated selected bodies without their dependencies. No frontend plugin or
background watcher is installed.

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
