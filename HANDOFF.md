# Implementation handoff

Updated: 2026-11-15.

## Current state and next-session request

`v0.0.5` at `9be43eb` is published on origin with wheel and source assets;
its Python 3.10–3.14 CI and release workflow passed. This release includes
comment-based source baselines and unpinned import destinations.

The post-release follow-up separates pure import-link syntax into
`src/load_clean/_import_link_format.py`, shared by IPython and static export.
`import_link.py` retains compatibility imports of its earlier syntax helpers.
The existing core/tooling package split remains useful; no package renames.

User specifically authorized protecting required imports before the next release.
Generated identifying imports and import-linked exports now carry `# noqa: F401`.
PyCharm documents noqa support; real Flake8 and Ruff checks confirmed that the
marker suppresses F401 and prevents Ruff from removing the import. The unmarked
control was removed. This is not a universal guarantee for every organizer;
explicit export policies such as `--imports remove-cells` still apply. README
and usage edits are limited to this authorized marker behavior.

The user primarily uses PyCharm and permitted verifying another frontend.
Actual JupyterLab 4.6.6 UI checks in headless Brave verified visible cell
replacement, notebook edits saved to the module, file edits refreshed into the
cell, updated execution results, no successful-sync output, and conflict refusal
without file writes or execution of conflicting edits. PyCharm UI remains
unverified. Kernel requests still do not acknowledge frontend application.

Verification: 192 tests passed without skips; isolated sdist/wheel builds passed;
a core-only installed wheel outside the checkout verified parser compatibility,
reference comments, protected imports and optional-dependency separation.
Temporary browser/server/environment artifacts are removed after verification.
No human usability measurements were made.

## Decisions awaiting approval

The user requires approval before further user-facing changes. Do not treat
previous conversational proposals as approved. In particular:

- Simplify the public workflow to sync/copy/skeleton: rename inline to copy,
  visibly materialize independent code for copy/skeleton, and keep default/path
  forms compatible while removing them from the primary documentation.
- Extend status to primary sync links and doctor to package version/module path.
  Status currently records only default/inline/skeleton loads.
- Add a runnable sync example and task-based onboarding; the checked-in example
  currently demonstrates inline export. Preserve the existing export example.

The import-retention marker is already explicitly approved. No other interface,
mode, output or onboarding changes were made during this review.

## Contracts and verification commands

- Import links: bare magic, identifying import, separate source-hash comment,
  then editable source. The hash is not a Git commit and persists in saved cells.
- Selected edits preserve unselected module source. Both sides changing the
  selected source differently causes a conflict before writing or executing.
- Import-linked execution retains module/package context; path links execute in
  the notebook namespace. Runtime errors do not undo successful synchronization.
- Static check/build never synchronize source files. Import links export imports;
  path links export the saved notebook body. Legacy argument layouts remain read.
- Standard full suite:
  `PYTHONPATH=src IPYTHONDIR=/tmp/load-clean-ipython python -m pytest -q`.
  Notebook execution needs local kernel sockets and writable Jupyter data.
- Release tags must match `project.version`; never move published tags.

Read `docs/APPROACH.md` for the work protocol and existing design constraints.
Historical implementation details remain in Git and the append-only
`docs/approach-log.tsv`; completed unit briefs are no longer an active backlog.
