# Migration from the initial prototype

## Sync-on-run workflow

The primary interface is now a bare `%%load_clean` with `import module` or
`from module import name`. The first run loads an editable whole-module or
selected-definition link and executes in module context. Keep the generated
bare magic, import statement, and separate `# Referenced Source: sha256:...`
comment. The comment holds a source baseline, not a Git commit. Import links
resolve their destination from the import each Run. Earlier `--import` and
`--file`/`--base` headers still work and convert automatically on Run. Sync status and fallback
source displays have been removed; user code can still produce output.
Each Run synchronizes the changed side;
conflicting edits to the selected source error before writing or executing.
See [linked-cell semantics](usage.md#linked-cells-primary-interface).

Bare imports previously performed an ordinary import without creating a link.
Use explicit `%%load_clean default` to retain that behavior. `inline`, `skeleton`,
creation-only save, and whole-file path links remain available. Import links
export the original import and require the project at runtime; they do not export
isolated selected bodies without their dependencies. No frontend plugin or
background watcher is installed.

## Configurable exports

Existing notebook modes remain available. Build policies can now be chosen
independently of notebook syntax; the defaults still resolve load-clean cells,
retain imports, remove tagged/legacy cells, and clear saved outputs.

For example, `load-clean build dev_analysis.ipynb --strip-setup --no-clobber`
removes standalone extension setup cells and refuses an existing output.
`--load-clean strip` instead keeps the literal Python body, including unsynced
linked-cell edits, without resolving imports or checking baselines. Use that
policy deliberately; it does not provide module globals or package context.
`--load-clean keep` cannot be combined with execution.

See [build options and their limits](usage.md#build-and-inspect-notebooks) for
batch selection, destinations, cleaning, execution, and reporting controls.

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
