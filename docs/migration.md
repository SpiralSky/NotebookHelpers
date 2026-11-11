# Migration from the initial prototype

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
