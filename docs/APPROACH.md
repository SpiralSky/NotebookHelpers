# Approach: a clear notebook authoring and export experience

Created: 2026-11-14 · Last revisited: 2026-11-14 · Revision: 2 · Depth limit: 4

## Objective (level 0)

- **Wanted:** help a notebook author get from reusable Python helpers to a usable
  exported notebook, understand what each action does, and recover from mistakes
  without reading implementation code. The user explicitly made user experience
  the primary focus on 2026-11-14.
- **Working audience:** people who already use Python/Jupyter but are new to
  load-clean. This is an assumption, not a researched persona; teaching authors
  are a secondary workflow because skeleton mode already exists.
- **Measured by:** unassisted task completion, correct expectations about modes
  and execution, time to first successful export, and recovery from errors.
  Initial small-study thresholds below are planning guesses, not population
  estimates. A successful task must produce the correct artifact/result.
- **Constraints:** preserve default import semantics, explicit skeleton stubs,
  non-destructive editing, overwrite protection, opt-in execution, static source
  inspection, the limited embedding subset, optional dependencies and existing
  Python support. Correctness is a prerequisite for UX success.
- **Not required:** new GUI, new command names, broad Python support expansion,
  analytics infrastructure, or publication. Consider these only if observed
  friction justifies them. No participant recruitment or outreach is authorized.

## Revisit evidence and prior decisions

Baseline for UX comparisons: commit `3f66249` (runtime code unchanged from
`aff9448`). Read the full approach log: its only prior data row, line 2,
records planning and no prediction measurements. r1 D1, D2 and D3 were all
**never tested**; their deadlines are retired with the change in priority.
Their level-2 testing-method and level-1 resolver/notebook ascents changed the
plan, but payoff is **unknown**, not established or disproved. The reuse row
was not independent evidence. Retain existing correctness tests; defer the new
r1 differential-testing and fault-seeding program unless a UX task exposes a
relevant semantic risk. The prior full plan remains in commit `3f66249`.

The trigger is explicit user correction, recorded in log line 3. This is a
level-0 objective-framing correction: r1 skipped scope questions and treated
technical reliability as the main outcome. It is not an execution failure or
an observed failure of the testing methods. Reopen the skipped prioritization
question at level 2; there is no repeated failure warranting level 3.

Local observations (2026-11-14): README.md shows loading a helper but links away
for the full export workflow; docs/usage.md describes modes and several inspection
commands; cli.py prints paths for both build and check and passes through caught
error text; extension.py has distinct preview/check/materialize behavior. These
are design surfaces and hypotheses about friction, not observed user problems.
HANDOFF.md's passing-test report remains historical correctness evidence, not UX
validation. No usability participants or task timings have been observed.

Research consulted 2026-11-14:

- [NN/G research-method selection](https://www.nngroup.com/articles/which-ux-research-methods/)
  distinguishes behavioral evidence from reported preferences. Applied here:
  watch task completion before choosing improvements from feature requests alone.
- [NN/G task scenarios](https://www.nngroup.com/articles/task-scenarios-usability-testing/)
  recommends realistic goals without giving away the interface steps. Applied
  here: ask for an export or recovery outcome, not a named command sequence.
- [Command Line Interface Guidelines](https://clig.dev/#guidelines) supports
  discoverable help, useful examples, and understandable success/error feedback.
  Applied here: connect messages to the user's next action. Extension to notebook
  magics is our inference; project-specific benefit remains unmeasured.

## Level map

| Component | Level | Question | Choice and reason | Yield |
| --- | --- | --- | --- | --- |
| Choose UX work | 2 | How should candidate improvements be found and judged? | climb: governs every interface change | U1 prioritizes observed task blockers and tests outcomes rather than command counts |
| First use | 1 | How should a new author reach a first export? | climb: inspect quickstart through the task-scenario method | U2 proposes one complete runnable path, with advanced options later |
| Understand modes | 1 | How should users choose actions and predict their effects? | climb: inspect docs/magics using discoverability guidance | U3 ties existing modes and inspection actions to outcomes |
| Recover and confirm | 1 | How should failures and success lead to a next step? | climb: apply CLI help/error guidance to local outputs | U4 specifies actionable errors and distinct check/build feedback |
| First use, modes, recovery | 2 | How should their UX methods be evaluated? | reuse: U1 applies across these activities | Unassisted behavior and comprehension, not three independent confirmations |
| Correctness and packaging | 1 | How should valid behavior be preserved? | reuse: existing tests and CI, with targeted regressions when behavior changes | Reliability remains a gate, not the UX success metric |
| Correctness research | 2 | Should differential/fault-testing infrastructure lead the next unit? | skip: user redirected priorities and r1 has no measured return | Defer r1 experiments |
| Research selection | 3 | Does choosing UX research methods need its own investigation? | skip: no repeated method failure | Stop at level 2 |
| Effort allocation | 4 | Should deeper recursion replace small experiments? | skip: no cross-project return evidence | Experiment before further research |

## Decisions

### U1: prioritize observed obstacles in complete user tasks

- **Level:** 2.
- **Governs:** U2–U4 use realistic tasks, unassisted completion and comprehension;
  choose the first implementation from an observed blocker, not code complexity.
- **Rejected alternative:** implement a broad heuristic redesign immediately.
  Heuristic review is a cheap way to propose candidates but cannot demonstrate
  user benefit. A survey-only approach measures preference, not task success.
  Product telemetry was considered and deferred: this local tool has no established
  usage volume, and observation can expose causes without adding collection.
- **Support:** researched — NN/G method selection and task scenarios, 2026-11-14;
  the local audience, sample size and thresholds are guesses.
- **Prediction:** within six implementation sessions, across two distinct UX
  iterations, at least two observed task failures or requests for help on the
  baseline become unassisted successes on equivalent revised tasks, with no new
  critical misunderstanding of execution or source modification.
- **Baseline:** preserve baseline transcripts and version; use equivalent tasks
  and alternate version order where practical. Report participant familiarity
  and learning effects; do not claim causality from an uncontrolled repeat.
- **Test:** start with one actual notebook author's walkthrough; validate candidate
  fixes with three target users where available. Record task, outcome, elapsed
  time, help, expectations and evidence location. A developer/agent walkthrough
  can find defects but cannot count as user evidence. No observed baseline
  problems means there is no demonstrated gain; do not manufacture one.
- **Revisit if:** no improvement across two iterations, the audience assumption
  is wrong, or participant evidence is unavailable by the deadline.
- **Status:** untested.

### U2: offer one complete first-use path before advanced choices

- **Level:** 1.
- **Decision:** connect source-checkout installation, environment/kernel setup,
  creating a helper, using it in a notebook, exporting, and locating the result
  in one runnable example. Explain expected output at each transition; link to
  advanced inspection, synchronization and teaching options afterward.
- **Rejected alternative:** start with a full command/mode catalog; it requires
  newcomers to assemble the workflow before experiencing the result.
- **Support:** reasoned — local README/usage inspection plus task-oriented design
  guidance, 2026-11-14. It is not established that documentation alone suffices.
- **Prediction:** within three implementation sessions, at least two of three
  new-to-load-clean notebook users produce and locate the intended clean export
  within 15 minutes without coaching or source-code inspection, using the revised
  path from a prepared checkout with Python/Jupyter available. Record dependency
  installation time separately; exclude external download waiting from the timer.
- **Baseline:** current README and linked docs, same environment and equivalent
  helper/notebook task; record completions and time, including failures.
- **Test:** first verify the literal instructions locally, then observe the task
  with human users. Automated execution only establishes that instructions run.
- **Revisit if:** threshold is missed, kernel/setup issues dominate, or users
  need a different installation route. Do not promise a published distribution.
- **Status:** untested.

### U3: explain actions through their effects on code and execution

- **Level:** 1.
- **Decision:** give a compact outcome-based choice: keep ordinary imports,
  embed supported definitions, or make exercise stubs. Explain preview, check
  and materialize at the point they help, including whether code runs or a new
  cell appears. Preserve existing syntax initially.
- **Rejected alternative:** rename or merge commands immediately. Discoverability
  may improve with wording alone, while syntax changes impose migration costs.
- **Support:** reasoned — documented semantics and CLI discoverability guidance,
  2026-11-14; wording effectiveness is a hypothesis.
- **Prediction:** within three implementation sessions, all three pilot users
  correctly choose outcomes for import reuse, embedded source and exercise stubs,
  and correctly predict execution/no-execution for preview, check and materialize,
  without assistance. No participant claims embedding includes all dependencies.
- **Baseline:** current docs, with equivalent scenarios rather than recalled answers.
- **Test:** ask users to choose and explain before running an action; verify their
  expected effects against the product. Ask neutral questions without naming the
  desired command. This is a small diagnostic pilot, not a statistical estimate.
- **Revisit if:** any execution misconception persists, or correct mode selection
  still requires reading implementation details.
- **Status:** untested.

### U4: make feedback explain the result and a viable next action

- **Level:** 1.
- **Decision:** errors identify the affected input/cell when available, explain
  the cause in user terms, and offer a valid recovery step. Success distinguishes
  validation without writing from a written export and states where to find it.
  Preserve exit codes and script compatibility when adjusting CLI output.
- **Rejected alternative:** append generic troubleshooting advice to every error;
  it adds noise without ensuring the suggested action can resolve that failure.
- **Support:** researched — CLI error/help guidance, 2026-11-14; local issue
  prevalence is unknown, so choose actual observed blockers first.
- **Prediction:** within four implementation sessions, at least two of three pilot
  users recover unaided within three minutes per case from a missing source path
  and an unsupported embedding request, and all three identify whether check or
  build wrote a file. Recovery may use a documented supported alternative; it
  must still satisfy the task, not silently abandon the desired export.
- **Baseline:** current messages for identical error categories and equivalent inputs.
- **Test:** prepare recoverable fixtures before observing users; verify suggested
  actions actually work, then time recovery. Record any facilitator hint as help.
- **Revisit if:** suggested fixes fail, recovery thresholds are missed, users assume
  check executed code, or improved messages break a documented script interface.
- **Status:** untested.

## Experiment order

1. U1/U2: establish a baseline first-use walkthrough and identify the largest
   observed blocker. Prepare a complete journey prototype; this tests the least
   supported audience/workflow assumptions before substantial interface changes.
2. U3: test choices and expectations alongside the prototype before changing syntax.
3. U4: address observed recovery/feedback problems and run the fixed scenarios.
4. U1: evaluate returns across two iterations before widening scope. If people
   are unavailable, continue reproducible instruction/message checks, label them
   technical evidence, and leave human UX predictions inconclusive.

## Project revisit triggers

- Any broken prediction or the user changes the audience/workflow priority.
- A task succeeds technically but users misunderstand execution or modification.
- Existing correctness checks regress, or a UX proposal changes a mode contract.
- Two iterations do not improve the observed bottleneck.
- Participant evidence is missing at a prediction deadline; revise feasibility,
  not the observed result. Do not count agent role-play as a human study.

## Work-session protocol

1. Read this file before choosing work; do not load the approach skill.
2. One unit per session. Default next unit: a runnable first-use journey prototype
   and neutral baseline task script. Use available user feedback; obtaining human
   participants requires their availability, not unsolicited outreach.
3. Deadlines count implementation sessions after r2. Freeze task outcomes and
   scoring before testing. Keep failures, help and exclusions in the evidence.
4. Run relevant technical checks for changed behavior. Existing full suite:
   `PYTHONPATH=src IPYTHONDIR=/tmp/load-clean-ipython python -m pytest -q`.
   Retain CI version/package checks; passing them does not prove usability.
5. Append one row per tested prediction to approach-log.tsv, using U1–U4 IDs,
   measured outcomes, baseline, verdict and an evidence path/commit. If nothing
   was tested, use decision `-` and verdict `not-tested`. Preserve all prior rows.
6. Commit the unit and report results and limitations. Recommend `$approach revisit`
   when a trigger fires; do not change thresholds during implementation.

## Revision history

- r1 2026-11-14: created correctness-focused approach; no predictions tested.
- r2 2026-11-14: user explicitly prioritized UX. Log line 2 establishes no prior
  measurements; line 3 records this correction. Deferred r1 D1–D3 without claiming
  they failed. Researched UX method selection and task/feedback design; introduced
  U1–U4 with untested predictions. No measured UX or ascent payoff yet.
