# Implementation handoff

Updated: 2026-11-15.

## Current state and next-session request

`v0.0.5` at `9be43eb` remains the latest release. Follow-up `de94bde`
separated pure import-link syntax and protected identifying imports with noqa.
The resumed session recovered subsequent user approvals from the previous
session transcript; the old handoff’s pending-approval list was stale.

Completed the approved follow-up:

- `copy` inserts independent Python without executing it; `skeleton` also
  materializes without execution. Both omit dependency imports by default;
  `--include-imports` retains supported imports. Legacy `inline` still executes
  immediately with imports, and explicit `default`/path forms remain compatible.
- Sync always includes top-level module imports, editable alongside selected
  definitions. Shared imports participate in conflict detection; unselected
  definitions and surrounding text are preserved. Other globals/conditional
  blocks remain file context. Changed imports group at the first existing import;
  first imports preserve module docstrings, preambles and decorators.
- Status includes selected/whole-module/path sync links without executing or
  writing. Doctor shows distribution version, module/CLI paths and dependencies.
- `examples/dev_sync.ipynb` and `examples/sync_helpers.py` demonstrate the workflow;
  the existing export example remains unchanged. Guidance emphasizes sync/copy/
  skeleton while documenting compatibility syntax.

The user subsequently requested push and tag. Implementation `35864a7` was
pushed, but tag `v0.0.6` accidentally preceded the blocked version commit and
points to package version 0.0.5; its release CI must fail. Preserve that published
tag. Version 0.0.7 is prepared as the corrected release; CI gates release assets.
Future work should follow concrete user feedback; do not infer authorization
for unrelated interfaces.

## Verification and limits

All 210 tests passed without skips; isolated sdist/wheel builds and core-only
installed-wheel checks outside the checkout passed. Results are recorded in
`docs/approach-log.tsv`. Both documented
example check/build commands and raw sync notebook execution passed in a disposable
copy; inputs stayed unchanged. Kernel checks verify replacement requests, not
visible frontend application. The earlier JupyterLab 4.6.6 UI check passed;
PyCharm UI and human usefulness remain unverified.

Old saved selected links refresh with imports when unchanged. Edited older links
may conflict because their digest excluded imports: preserve edits, load a fresh
link and transfer edits manually. Static export of saved old links remains valid.

## Contracts and verification commands

- Import links retain an identifying import plus separate source hash comment.
  The hash survives notebook saving/restarts and is not a Git commit.
- Sync conflicts stop before writes/execution. Writes validate syntax, recheck
  bytes and publish atomically; runtime errors leave completed syncs saved.
- Selected execution retains module/package context; path execution uses the
  notebook namespace. Run dependent calculations again after syncing.
- Build/check never sync source files. Import links export protected imports;
  path links export saved Python; copy/skeleton requests resolve statically.
- Full suite: `PYTHONPATH=src IPYTHONDIR=/tmp/load-clean-ipython python -m pytest -q`.
  Notebook execution requires optional dev dependencies and local kernel sockets.
- Release tags must match `project.version`; never move published tags.

Read `docs/APPROACH.md` before choosing work. The append-only approach log
records technical evidence separately from unmeasured human benefit.
