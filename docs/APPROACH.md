# Approach: rapid notebook experiments with maintainable Python files

Created: 2026-11-14 · Revisited: 2026-11-14 · Revision: 3

## Decision and objective

Make the experiment → reusable module → notebook feedback → Git review → delivery
loop the primary experience. Export is one stage, not the whole product. Preserve
ordinary Python imports and an explicit source of truth. Offer Jupytext pairing
for notebook history, modules for reusable code, and load-clean embedding when a
recipient needs selected source inside a notebook.

This revisits r2 following the user's explicit request to retain rapid notebook
testing while saving files for Git and structured development. r2 overemphasized
first export and treated human studies as the default gate for choosing work.
Proceed with reversible improvements supported by code inspection and existing
tool documentation; use human observation when available to test usefulness.
Do not make participant availability a prerequisite for fixing known gaps.

## What the review established

These are implementation observations, not measured user difficulties:

- `extension.py` loads, previews, checks, and materializes file definitions. It
  has no notebook-to-module save operation. Materialize creates a new input cell;
  it does not write a Python file or maintain a round trip.
- `notebook_builder.py` reads `.ipynb` or `py:percent`, removes marked cells,
  resolves load-clean magics, and clears prior outputs. Execution is opt-in.
  Explicit file selection works with paired notebooks; directory selection
  rejects pairs as output collisions. Build does not synchronize pairs.
- `load-clean pair` and `load-clean sync` now wrap Jupytext for one explicit
  notebook/percent pair, report content changes, and refuse ordinary helper
  modules and directory scanning. Build ambiguity names both explicit choices.
  Sync uses saved-file recency; it does not detect divergent edit history.
- Default imports have normal Python cache behavior. Inline definitions are a
  snapshot until rerun. Source status detects changes but does not refresh
  computations or prove that notebook results match source on disk.
- Verification found that the installed CLI entry point cannot resolve an
  uninstalled helper merely by changing directories. The runnable guide uses
  `python -m load_clean_tools.cli`; P3 should address source-path discoverability.
- README previously began with modes, omitted a complete runnable export, and
  did not explain saving experiments, reloading modules, or Git pairing.
- The current `src/load_clean` core/extension and `src/load_clean_tools` tooling
  split is useful. Moving packages adds import churn without addressing this
  workflow. Keep it; reorganize user guidance by task instead.

## Evidence that changed the choice

Research consulted 2026-11-14. These sources document capabilities and limitations;
none measures usability improvements in this project.

| Question | Finding and source | Decision and project action |
| --- | --- | --- |
| Build custom notebook/text synchronization? | [Jupytext pairing](https://jupytext.org/using/paired-notebooks/) already keeps text inputs and notebook outputs; newer inputs and concurrent editor saves need care. | Reuse Jupytext. Document explicit synchronization and one-file build selection; do not implement another merge engine. |
| How can module edits retain rapid feedback? | [IPython autoreload](https://ipython.readthedocs.io/en/stable/config/extensions/autoreload.html) refreshes imports before execution, with documented limits. | Recommend ordinary imports plus autoreload for development; fresh-kernel execution remains the reproducibility check. |
| Is notebook-to-file saving already solved by a magic? | [IPython writefile](https://ipython.readthedocs.io/en/stable/interactive/magics.html#cellmagic-writefile) writes a whole cell and overwrites the file by default. | Document it for small new files with clear ownership transfer. A future convenience action must protect existing modules and avoid an ambiguous second editable copy. |
| Should load-clean become a notebook package framework? | [nbdev's tutorial](https://nbdev.fast.ai/tutorials/tutorial.html) describes notebook-driven modules, testing, documentation, and package work. | Recommend evaluating nbdev for notebook-authoritative libraries. Keep load-clean focused on ordinary modules and selective notebook delivery unless user needs justify framework scope. |

The governing question was how to choose the authoring model: distinguish artifact
roles and authority before choosing commands. That changed the lower-level choice
from expanding export controls to documenting the full loop and prioritizing
promotion into modules. No deeper research into research methods is warranted:
there is no consequential unresolved method-selection question here.

**Strongest alternative:** notebook-authoritative development with nbdev. Prefer
it if users want to keep library definitions, tests, and narrative together in
notebooks indefinitely. Our provisional default instead transfers ownership of
mature definitions to modules; it fits the existing implementation and standard
Python tooling. The user's preference between these authoring models remains
unmeasured. Reconsider before building multi-cell package export or round-trip
function editing.

## Prioritized work and acceptance conditions

| Priority | Unit | Done when |
| --- | --- | --- |
| P0 — this session | Reorganize onboarding around the complete development loop | README has a runnable export; workflow explains pairing versus modules, reload behavior, source ownership, Git review, and generated artifacts; literal commands receive technical verification. |
| P1 — complete | Safe promotion of a prototype cell into a module | User can preview destination/content, create a new module without implicit execution, and get a usable import. Existing files are refused by default; any replacement is explicit and atomic. Invalid Python leaves files unchanged. Document removing the old definition/writer cell and adding a test. Start with whole-cell/new-file scope, not AST merging. |
| P2 — complete | Pairing and build selection experience | Provide a discoverable route to Jupytext pairing/sync. Identify pair ambiguity with concrete valid file choices; do not silently select a stale side. Preserve outputs and report whether files changed. Test conflicts and missing optional dependencies. |
| P3 | Feedback and reproducibility | Distinguish check from write while preserving script compatibility, identify source and destination, and explain stale inline snapshots. Verify edited-module feedback and fresh-kernel behavior; never imply a static check executes code. |

P2 ships explicit `pair --source FILE` and `sync --source FILE` commands. Pair
refuses an existing counterpart; sync requires recorded `ipynb,py:percent`
metadata. Output preservation follows Jupytext matching-cell rules. Build/check
keep path-only stdout and never implicitly sync. P3 remains next.

P1 ships `%%load_clean_save [--preview] path.py`: whole-cell creation with
existing parents, symlink refusal, and atomic publication without replacement.
Do not promise automatic dependency extraction, safe arbitrary merging, or
bidirectional editing. Reorder this queue if actual user feedback identifies a
larger obstacle. A GUI, broad resolver expansion, and package renames are deferred.

## Validation and remaining uncertainty

Technical checks establish that commands work, artifacts are correct, and original
files survive. They cannot establish that new users find the workflow convenient.
No user task observations, completion timings, or measured UX benefit exist yet.

When a notebook author is available, use these neutral tasks: experiment with a
function and make it reusable outside the notebook; change it and obtain a current
result; review the change in Git; deliver a working notebook to a colleague.
Observe where they need help, which file they believe owns the function, and
whether they can identify stale results. Record environment and prior experience.
Do not count agent walkthroughs as participant evidence or impose invented
completion thresholds. Test destructive edge cases automatically before a new
save action is offered.

r2 U1–U4 predictions remain **untested**, not failed. Their session deadlines are
retired because the objective and feasible evidence collection changed; no
success is claimed. Keep their definitions in Git history and the append-only
log. If human validation resumes, define outcomes before observation and preserve
failures/help rather than retroactively applying r2 thresholds to different tasks.

## Technical verification of this revision

2026-11-14, Python 3.14, temporary editable installation with the dev extra:
all 27 existing tests passed. In a disposable copy of `examples`, ran the README
module CLI build with execution; paired with Jupytext 1.19.6; inserted and executed
the tagged extension setup cell; saved and synchronized; checked the text source;
and built/executed the text source. Verified the initial source stayed unchanged
by build, check created no output directory, setup was removed from the export,
no load-clean cell magic remained, and output was `Hello, world!`.

Initial checks in the base environment had 24 passes and 3 dependency skips.
Installing dependencies and allowing local kernel sockets enabled the full check.
The first installed-entry-point walkthrough failed to locate `example_helpers`;
the corrected documented module invocation passed. No GUI interaction or human
usability study was performed. These are technical checks, not UX measurements.

## Work-session protocol

1. Read this document before choosing work. Ordinary implementation does not need
   the approach skill; an explicit approach revisit does.
2. Do one bounded unit, built/checked and committed. P1 and P2 are complete; the next unit is P3.
   Read only current handoff state if needed; keep the queue here authoritative.
3. Preserve default imports, explicit skeleton stubs, optional dependencies,
   static inspection, non-destructive editing, and opt-in execution. Existing
   generated build targets may be replaced; source inputs may not.
4. Run relevant checks. Existing full suite:
   `PYTHONPATH=src IPYTHONDIR=/tmp/load-clean-ipython python -m pytest -q`.
   For documentation workflows, run the actual commands in a disposable copy.
5. Append measurements to `docs/approach-log.tsv`. If no user prediction was
   tested, use decision `-`, verdict `not-tested`, and record technical evidence
   separately from UX outcomes. Never rewrite past rows.
6. Report changes, verification, limitations, and commit. Revisit when user
   authoring preferences change, the next feature duplicates an existing tool,
   or observed workflow failures contradict the current priority.

## Revision history

- r1: correctness-focused planning; no measured prediction outcomes.
- r2: first-export UX and pilot-study proposals; no human measurements.
- r3: full development-loop framing, existing-tool comparison, task-based docs,
  and a bounded implementation queue. Benefit to users remains unmeasured.
