# Implementation handoff

Updated: 2026-11-14. Baseline: `0edf184` on `main`.

## Current state and next-session request

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

Start here. Relevant files:

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

Relevant files: `src/load_clean_tools/sync.py`, `cli.py`,
`notebook_builder.py`, `tests/test_builder.py`, and the workflow/reference docs.
Add focused sync tests if a separate file is clearer.

The current `sync()` scans every top-level `.py` file and calls Jupytext. It is
not exposed through the CLI and is not a safe template for blindly processing
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
