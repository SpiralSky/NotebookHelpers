# Implementation handoff

Updated: 2026-11-15. Historical P3 baseline: `426802d` on `main`.

## Current state and next-session request

Sync wrapper follow-up: pair/sync now invoke the supported Jupytext CLI via
`sys.executable -m jupytext` with checked subprocess exit status, preserving quiet
path reporting. Nonzero exits become RuntimeError with the child failure chained;
the load-clean CLI returns 1. Verification: 17 sync tests passed on Jupytext 1.19.6,
covering both directions, both missing counterparts, preserved notebook outputs,
paths with spaces, interpreter selection, and failure propagation.

Documentation follow-up: README now provides the missing `helpers.py` prerequisite
and a runnable check/executed export using the checked-in example. Migration covers
configurable exports; the reference distinguishes parser and validation exit codes.
No runtime changes were needed. Verification: 175 tests passed without skips;
isolated sdist/wheel build passed. Disposable README commands produced
`Hello, world!`, preserved source bytes, and confirmed check writes nothing.
The documented import link returned 42 and requested an editable replacement.
Frontend application of that request remains unverified.

Build configurability follow-up: notebook syntax/modes are intentionally unchanged;
the user wants to discuss their removal separately. Build/check now accept multiple
positional or repeated --source inputs, recursive include/exclude selection, output
directory/file/suffix controls, dry-run, no-clobber, four load-clean policies,
import-only-cell removal, tag/output/metadata controls, execution settings and
quiet/verbose/NUL-delimited reporting. Defaults preserve previous behavior.
Batch destinations are preflighted; writes are individually atomic. Retained magics
cannot be executed by build, preventing accidental sync through --load-clean keep.
See the current build reference for semantics and limits.
Verification: 175 tests passed without skips; isolated sdist/wheel build passed.
Disposable CLI walkthrough verified literal stripping with fresh-kernel execution,
recursive filtered dry-run, exact output/no-clobber and snapshot preservation;
all source notebooks and helper files retained their original bytes.

Import-addressed follow-up: bare `%%load_clean` now accepts `import module` or
`from module import name` to create editable module/selected-definition links.
Generated headers preserve import identity, source path and selection baseline.
Selected edits replace source spans without rewriting unrelated code; aliases,
multiple names and package-relative imports are covered. Execution uses module
context. Re-exports/ambiguous bindings are rejected. Explicit `default` retains
the former bare-import behavior. Import-linked export preserves ordinary imports
and rejects unsynced cell edits; project dependencies remain required. Path links
remain available. This supersedes the whole-file limitation in the earlier entry.
Verification: 145 tests passed without skips; isolated source/wheel build passed.
A real kernel verified aliases, package-relative imports, selected saves preserving
unrelated edits, conflict refusal, source refresh, whole-module binding, and an
executed import-preserving export without source mutation. GUI replacement remains
unverified; custom meta-path loaders and re-export editing are unsupported.

2026-11-15: sync-on-run is now the primary workflow. `%%load_clean path.py`
synchronizes and executes a whole module; `%load_clean path.py` loads an existing
file into a new linked cell without execution. A persisted `--base` hash selects
sync direction and rejects differing simultaneous edits with a diff. Existing
magics remain compatible. Linked export uses the notebook body without reading
or writing its source file. Source updates use IPython replacement requests and
display a fallback cell; no frontend GUI hooks or watchers are implemented.
Whole-file ownership is deliberate; individual function merging is unsupported.
Verification: 117 tests passed without skips; isolated sdist/wheel build passed.
A real kernel verified create, save, source refresh, replacement payloads, and
conflict refusal. GUI application of replacement requests remains unverified.
See current README, workflow and usage; the implementation history below is older.

P1 is complete in `d672aad`: `%%load_clean_save`
previews or atomically creates a new whole-cell module without execution;
existing paths are refused and replacement is unsupported. Parents must exist,
symlinks are refused, and exports reject untagged save cells. Core save API,
file/race safety tests, magic tests, export workflow tests, and guidance are added.
Verification: 49 tests passed without skips (including fresh-kernel promotion
export); isolated sdist/wheel build passed. Initial socket/network sandbox
failures were resolved through normal escalation. No human predictions tested.
P2 is complete in the commit containing this update. `pair --source FILE` creates
an ipynb/percent pair and refuses an existing counterpart; `sync --source FILE`
requires recorded same-directory pairing and uses Jupytext's recency rules.
Both report exact created/updated/unchanged file paths by content bytes. Ordinary
helper modules/directories and unsupported formats are refused. Directory build
ambiguity names both inputs and shell-quoted explicit build choices. Build/check
retain path-only stdout and never synchronize. Docs explain saved/unsaved edits,
recency versus merging, reconciliation, and selecting one input deliberately.
Verification: 61 tests passed without skips; disposable pair/sync/check/build CLI
walkthrough passed with spaces in paths; isolated sdist/wheel build passed.
P3 and final integration are complete in `23ff1f5`.
Check/build retain path-only stdout, with static/no-write and source/destination
feedback on stderr. Explicit repeatable `--source-root` replaces static lookup
roots without mutating sys.path or importing helpers. Errors retain original
source cell numbers after removal and give recovery guidance. Doctor uses
source-checkout installation advice. Reload, snapshots, and status limits are
documented and tested.
Verification: focused suite 50 passed; full suite 66 passed, no skips. Isolated
sdist/wheel build passed. Clean core-only wheel verified both executables and
missing optional dependencies; separate wheel+dev environment reproduced the
example lookup failure, then verified explicit roots and both entry points.
A disposable complete preview/save/import/test/edit/reload/inline/pair/sync/Git/
check/executed-build workflow passed outside the repository. Preview/check made
no output; build/check preserved original helper and selected sources; fresh
kernel output was 400 and the export had no writer or development magic.
Kernel sockets/trust database and build/install network used normal escalation.
No implementation blockers remain. Human predictions remain untested. The
independent review found a save-cell rejection bypass through leading blank
lines. The follow-up commit containing this update fixes the confirmed finding
by checking the first non-whitespace line before import parsing. Regression
coverage confirms IPython would execute each blank-line variant, untagged cells
are rejected, tagged cells are removed before parsing, and a marker inside a
Python string is preserved. Targeted regressions: 9 passed (16 deselected).
Full suite after the fix: 74 passed, no skips; isolated sdist/wheel build passed.
The one-time independent review is complete; no further review loop requested.

The user requests a handoff for implementing **all remaining work** from the UX
review in the next session. This document covers P1–P3 and final verification.
Read `docs/APPROACH.md` for the governing decisions, then execute the backlog in
order, using bounded commits. This explicit request sets the intended scope;
do not mistake the earlier default “next unit is P1” for the full requested scope.
Do not spawn subagents unless the user asks. No push or release is requested.

P0 is complete: README and `docs/workflow.md` cover experiment → module → Git →
export; `docs/usage.md` remains the reference. Runtime code was not changed.
All 27 existing tests and a disposable pairing/executed-export walkthrough passed
with optional dependencies installed. No human usability measurements exist.

The objective is rapid notebook experimentation with maintainable, reviewable
files. Distinguish notebook text pairing from promoting functions into a library.
Keep ordinary modules authoritative after promotion. Keep the existing package
layout; do not spend the session on package renames or another approach review.

## P1: safely promote a prototype cell into a module

Completed. Original contract retained below. Relevant files:

- `src/load_clean/extension.py`: `LoadCleanMagics`, error handling, current
  preview/check/materialize/status conventions.
- `src/load_clean/api.py`, `src/load_clean/models.py`: inspect before choosing
  where a small independently testable save API belongs.
- `src/load_clean_tools/notebook_builder.py`: cell filtering and export behavior.
- `tests/test_magic.py`: shell fixture and non-destructive magic expectations.
- `docs/workflow.md`, `docs/usage.md`: replace manual-only guidance once supported.

Implement a notebook action that previews and writes a whole Python cell to a
module without executing its body. A proposed spelling is `%%load_clean_save`
with a path and explicit preview/replacement options; naming is not settled.
Choose syntax consistent with the existing magics and document it. No user
confirmation is needed for routine interface choices within this contract.

Acceptance:

1. Preview shows the resolved destination and exact source, with no writes,
   directory creation, imports, or execution.
2. Creation writes valid Python to a new `.py` file. Invalid source, invalid
   destinations, or a failed write leave existing files intact. Preserve source
   comments and formatting; this is not an AST rendering operation.
3. Existing destinations are refused by default. Any supported replacement must
   be explicit and atomic. Protect default creation against a destination that
   appears between validation and writing; do not silently overwrite it. Decide
   and document parent-directory and symlink behavior.
4. Report what was written and give an import that works for supported layouts.
   Do not infer a valid import merely from a filename when its parent is not on
   Python's import path. Explain editable installation or the source-path setup
   when needed. Do not run the import automatically.
5. Make ownership transfer clear: users replace the prototype/writer cell with
   an import and move stable behavior into a test. Do not silently rewrite their
   existing notebook cell. Re-running a remaining save cell must not destroy
   later module edits without an explicit replacement request.
6. Specify export behavior for save cells. A generated notebook must not retain
   an accidental module-writing step in the normal documented journey. Use the
   established `load-clean-remove` tag where appropriate; explain it and verify
   the complete workflow. Do not assume `%%load_clean_save` is parsed as the
   existing import-selection magic.

Test preview side effects, new-file creation/import, exact content preservation,
existing-file refusal, invalid Python, write failures, explicit replacement if
provided, and notebook execution state. A body containing an observable side
effect must be saved without running it. Avoid importing IPython in the core API.

Out of scope: merging functions into existing modules, automatic dependency
capture from kernel state, multi-cell package export, automatic bidirectional
editing, and replacing nbdev. Missing globals remain the author's responsibility.

## P2: make pairing/synchronization and build selection discoverable

Completed. Original contract retained below. Relevant files: `src/load_clean_tools/sync.py`, `cli.py`,
`notebook_builder.py`, `tests/test_builder.py`, and the workflow/reference docs.
Add focused sync tests if a separate file is clearer.

The pre-P2 `sync()` scanned every top-level `.py` file and called Jupytext. It was
not exposed through the CLI and was not a safe template for blindly processing
ordinary helper modules. Reuse Jupytext rather than building a merge engine.
Consult the installed API or official documentation for the actual version used.

Acceptance:

1. Offer a discoverable pairing/sync route through CLI help and docs. Prefer a
   thin explicit-file command over directory-wide mutation. Pairing and sync are
   distinct actions; report which files were created/updated or left unchanged.
2. Support notebook/`py:percent` pairs while preserving notebook outputs. Reject
   unsupported inputs and give actionable optional-dependency errors.
3. Explain that sync uses file recency, not semantic merging, and that unsaved
   editor changes are unavailable to the CLI. Do not claim reliable divergent-
   edit detection unless implemented with enough state to establish it. Provide
   an explicit route for choosing the intended input or reconciling copies;
   do not silently resolve ambiguity in build.
4. When directory build finds paired sources mapping to one target, identify both
   files and show valid explicit `--source` choices. Retain genuine collision
   and input-overwrite protections. Build must not implicitly synchronize files.
5. Verify pairing, edits on each side followed by deliberate sync, output
   preservation, ambiguity handling, missing optional dependencies, and paths
   containing spaces. Keep ordinary helper `.py` files out of broad sync actions.

## P3: feedback, source discovery, and current results

Completed; original acceptance contract follows.

Relevant files: `cli.py`, `notebook_builder.py`, `src/load_clean/extension.py`,
`src/load_clean/resolver.py`, corresponding tests, README and usage/workflow docs.

Acceptance:

1. Make check success explicitly say no output was written, and build success
   identify source and destination. Keep path-only stdout usable by existing
   scripts (for example, put explanatory messages on stderr). Preserve exit codes
   and the `load-clean-build` compatibility entry point.
2. Reproduce and address the installed-entry-point source-discovery problem:
   from `examples`, `load-clean build --source dev_example.ipynb --output ../build`
   cannot necessarily find uninstalled `example_helpers`, while
   `python -m load_clean_tools.cli ...` works. Choose a documented, predictable
   resolution policy or explicit source-root option; avoid global `sys.path`
   leaks, helper imports during static inspection, and unexpected module
   shadowing. Test the installed executable from outside the repository.
3. Errors include the relevant source/cell when available and a recovery step
   that actually works. Cover missing source paths, unsupported embedding,
   paired-input ambiguity, and absent optional dependencies. Correct doctor
   install advice for a source-checkout project; do not imply a published
   distribution was verified.
4. Explain current module files versus loaded inline snapshots. Default imports
   retain normal Python behavior; inline cells refresh only when rerun. Status
   may report changed source, but cannot certify that downstream results are
   fresh. Do not automatically execute cells to update results.
5. Verify the supported edited-module/ordinary-import feedback loop, rerunning
   inline definitions, and fresh-kernel notebook execution. Static check must
   never imply execution or successful runtime behavior.

## Integration and verification

Update README, workflow, command reference, examples where necessary, and the
approach queue to match shipped behavior. Include a concise end-to-end path:
prototype → preview/save → import/test → edit/reload → pair/sync → Git review →
check/build in a fresh kernel. Generated notebooks must not rewrite helpers or
require development-only magics in that documented path.

Run focused tests as each unit changes, then the full suite after integration:

```sh
PYTHONPATH=src IPYTHONDIR=/tmp/load-clean-ipython python -m pytest -q
python -m build
```

Use `python -m pip install -e '.[dev]'` in an isolated environment if dependencies
are missing. `/tmp/load-clean-ux-check` held the previous dev environment, but it
is disposable and must not be assumed to survive. The previous base environment
had 24 passes and 3 dependency skips; the full dev environment had 27 passes.
Do not report skipped integration tests as complete verification.

Notebook kernels need local sockets. The previous sandbox blocked those sockets
and dependency-network access; use the normal escalation mechanism when needed.
Git index writes also previously required escalation. Preserve all user changes.

Build a wheel and check its installation in an isolated environment, including
both CLI entry points, optional-dependency behavior, and the source-discovery
case. Run the workflow in a disposable project so tests cannot modify checked-in
examples. Verify original sources, output paths, execution results, and no writes
from preview/check. Review `git diff --check` and final status. Do not broaden
Python support claims beyond existing CI evidence.

Append results to `docs/approach-log.tsv` without editing past rows. Use decision
`-` and verdict `not-tested` when no human prediction was tested. Update this
handoff with completed commits and any exact remaining blockers. Commit the work
in coherent units and report tests, limitations, and whether all P1–P3 acceptance
conditions were met. Do not claim user benefit solely from automated success.

## Deferred work, not implementation blockers

Human observation is still unavailable: no unassisted task outcomes, timing, or
preference between module-authoritative and notebook-authoritative development
has been measured. If a real user becomes available, observe reuse outside the
notebook, edited results, Git review, and delivery; record help and misunderstandings.
Do not recruit or contact people without authorization. Retired r2 U1–U4
predictions remain untested; their deadlines do not restart.

A GUI, broader static Python embedding support, a custom synchronization engine,
package renames, nbdev-style package authoring, and automatic function merging
remain deferred. Revisit only if new user needs justify expanding scope.
