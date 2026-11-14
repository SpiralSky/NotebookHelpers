# Approach: reliable notebook exports

Created: 2026-11-14 · Last revisited: 2026-11-14 · Revision: 1 · Depth limit: 4

## Objective (level 0)

- **Wanted:** load selected Python definitions during notebook development and
  export usable notebooks without `%%load_clean` cells. This objective is inferred
  from README.md and docs/usage.md; no new product direction was supplied.
- **Measured by:** supported inline examples agree with ordinary imports on
  declared observable results; unsupported examples fail explicitly; exported
  notebooks execute with expected results; source notebooks remain unchanged.
  Target and minimum for each fixed experiment corpus: 100% of cases meet their
  declared contract, zero silent mismatches, zero source modifications.
- **Constraints:** retain default import semantics, explicit skeleton stubs,
  static source inspection without importing parent packages, opt-in execution,
  a core without IPython dependencies, and the Python 3.10–3.14 CI matrix.
  Embedding is a limited Python subset, not a sandbox or universal equivalence
  guarantee. Preserve overwrite/collision protection and pre-1.0 support policy.
- **Not required:** arbitrary Python embedding, dependency vendoring, PyPI
  publication, API stability, performance targets, or a feature expansion.

## Evidence and baseline

Inspected 2026-11-14: README.md, docs/usage.md, docs/support.md,
tests/test_resolver.py, tests/test_builder.py, src/load_clean/resolver.py,
pyproject.toml, and .github/workflows/ci-release.yml at baseline `aff9448`.
HANDOFF.md reports 27 passing tests, notebook execution, distribution builds,
and installed-wheel checks. These are historical results, not rerun measurements.
The suite already checks selected runtime outputs, rejection, and one executed
notebook; this approach adds systematic comparisons, not the first runtime tests.
The global lessons file was read and contained no findings or return measurements.

Research consulted 2026-11-14:

- [Csmith project](https://github.com/csmith-project/csmith) and
  [Yang et al., PLDI 2011](https://www.flux.utah.edu/paper/yang-pldi11):
  differential testing compares program behavior; meaningful comparisons require
  controlled program semantics. Transfer to Python source embedding is an
  inference, not evidence of effectiveness in this repository.
- [NBClient execution documentation](https://nbclient.readthedocs.io/en/latest/client.html):
  notebook execution supports explicit kernel, working directory, timeout, and
  error handling. This supports a reproducible execution experiment, not a
  guarantee that these notebooks are portable.

## Level map

| Component | Level | Question | Choice and reason | Yield |
| --- | --- | --- | --- | --- |
| Select scope | 1 | Which user workflows should govern work? | skip: retain documented modes until evidence contradicts them | Existing scope retained; no new feature backlog |
| Select scope | 2 | How should competing user needs be ranked? | skip: no competing requests or usage data | Revisit on user feedback |
| Validate transformations | 2 | How should correctness-testing methods be selected and judged? | climb: governs repeated resolver and export changes | D1 selects behavioral comparison and a small fault-detection comparison, rather than test count as evidence |
| Validate transformations | 1 | How should supported and unsupported cases be checked? | climb: apply D1 to existing tests and resolver | D2 adds fixed import/inline pairs and explicit rejection cases |
| Validate notebook workflow | 1 | How should exported artifacts be exercised? | climb: examine NBClient and existing execution test | D3 specifies fresh-kernel execution and source hashes alongside static checks |
| Validate notebook workflow | 2 | How should workflow validation methods be judged? | reuse: D1's within-project criterion applies | Use observable results; not an independently confirmed ascent |
| Package and distribute | 1 | How should installations be validated? | skip: existing wheel isolation and version matrix cover documented contract | Keep CI; no new packaging system |
| Package and distribute | 2 | How should packaging validation be chosen? | skip: no unresolved packaging evidence | No change |
| Allocate research | 3 | Which method investigations deserve repeated study? | skip: no logged method failures yet | Stop at level 2 |
| Allocate research | 4 | How much effort should each level receive? | skip: no cross-project returns in lessons | Use the skill's default diminishing effort |

## Decisions

### D1: judge testing methods by behavioral discrepancies they detect

- **Level:** 2.
- **Governs:** D2 adds import/inline comparisons; D3 checks executed notebook
  outputs and unchanged inputs. Existing test count alone cannot validate either.
- **Rejected alternative:** expand example/string assertions alone. They remain
  useful regressions but can miss a valid-looking export with changed behavior.
  Broad randomized generation, as used in compiler testing, was considered;
  defer it because a valid Python-subset generator and oracle would be additional
  infrastructure before the smaller method has demonstrated value.
- **Support:** researched — Csmith and local test inspection, 2026-11-14;
  effectiveness here is unmeasured.
- **Prediction:** within four implementation sessions, across three distinct
  changes or test exercises, the added behavioral checks detect at least one
  incorrect export missed by the unchanged baseline suite, with zero unresolved
  false alarms on the agreed supported cases.
- **Baseline:** tests at `aff9448`, run against the same candidate faults.
- **Test:** freeze three plausible isolated faults before comparing suites:
  wrong alias binding, wrong dependency constant, and an incorrect value in a
  notebook output not asserted by the baseline. Use temporary copies; retain
  case definitions and detection results. Report seeded faults separately from
  real bugs; a result on seeds does not establish a production defect rate.
- **Revisit if:** no incremental detection by the deadline, an unresolved false
  alarm, or the oracle needs the same resolver logic it is meant to check.
- **Status:** untested. Research changed the method; payoff is unknown.

### D2: preserve a bounded embedding contract and test it against imports

- **Level:** 1.
- **Rejected alternative:** silently broaden static inference or import modules
  while resolving source. This weakens explicit failure and inspection guarantees.
- **Support:** reasoned — documented contract and resolver/test inspection,
  2026-11-14; the proposed corpus size and adequacy are guesses.
- **Prediction:** within two implementation sessions, all six supported cases
  (alias, annotated constant, imported-library dependency, nested scope, class
  method, and function default) match ordinary-import results; all three declared
  unsupported cases (dynamic globals lookup, relative dependency import, repeated
  definition) raise explicit resolution errors before an export is written.
- **Baseline:** execute the original helper through an ordinary import in a
  separate process under the same environment and inputs. Compare return values,
  relevant output, and exception types, not generated source formatting.
- **Test:** freeze small deterministic fixtures and expected support labels before
  running; compare imports and inline output in isolated processes. Separately
  retain the existing skeleton NotImplementedError and default-import tests.
  Parent-initializer nonexecution is a separate inspection contract, not a demand
  for equivalence with arbitrary import-time side effects.
- **Revisit if:** any accepted case differs, a rejected case silently exports,
  or a real user workflow requires a case outside this contract. Do not relabel
  a failing supported case after observing its result to pass the prediction.
- **Status:** untested.

### D3: validate clean exports in a fresh kernel with explicit outputs

- **Level:** 1.
- **Rejected alternative:** treat successful static check/compilation as sufficient
  workflow evidence. It cannot reveal missing runtime dependencies or cell state.
- **Support:** researched — NBClient documentation and existing example execution
  test, 2026-11-14; broader effectiveness remains unmeasured.
- **Prediction:** within three implementation sessions, two notebooks (the existing
  example and one combining default imports with inline dependencies) build and
  execute in fresh kernels with all predeclared outputs correct, zero remaining
  load_clean cell magics, and byte-identical source files; a third notebook with
  an intentional runtime failure makes execution fail visibly.
- **Baseline:** static check of the same inputs, with its result recorded separately.
- **Test:** use temporary output directories, hash sources before/after, declare
  the intended helper/dependency paths, kernel and a finite 60-second cell timeout,
  and disallow ignored errors. A clean export need not vendor its dependencies.
  Keep existing overwrite and collision tests. Missing dependencies or kernel
  startup failures make the experiment inconclusive, not passed.
- **Revisit if:** outputs differ, errors are suppressed, a source changes, or a
  notebook only works with prior interactive kernel state.
- **Status:** untested.

## Experiment order

1. D2: test the smallest semantic corpus first; silent wrong code is costly and
   supported-boundary assumptions are least established. Record before fixing.
2. D3: exercise the complete export workflow after the resolver comparison.
3. D1: collect the paired detection results across the first four implementation
   sessions; do not infer a higher-level payoff from a single passing example.

## Project revisit triggers

- Any broken prediction, silent accepted mismatch, or input modification.
- Two consecutive relevant sessions cannot complete an experiment; distinguish
  environmental/execution failure from a flaw in the chosen method.
- User feedback changes the objective or contradicts the supported subset.
- A supported Python/dependency/environment change invalidates a test assumption.
- At the fourth implementation session, assess all deadlines and ascent returns.
  Missing measurements remain inconclusive; they are never evidence of success.

## Work-session protocol

1. Read this file before choosing work; do not load the approach skill.
2. Work on one unit in experiment order, unless the user directs otherwise.
   Session deadlines count implementation sessions after r1, not this planning
   session. Record case definitions and thresholds before observing results.
3. Run relevant tests, then commit the unit. Existing full-suite command:
   `PYTHONPATH=src IPYTHONDIR=/tmp/load-clean-ipython python -m pytest -q`.
   Keep CI packaging and Python matrix checks for release validation; do not claim
   a local Python run verifies that matrix.
4. Append one TSV row per tested prediction to approach-log.tsv, with measured
   counts, an evidence path or commit, baseline results, and held/broke/inconclusive.
   If nothing was tested, append one row with decision `-` and verdict `not-tested`.
   Record failures before repair and keep the log append-only.
5. Report a fired trigger and recommend `$approach revisit`. Ordinary work sessions
   do not rewrite this approach or relax thresholds. Revisit records global lessons
   only when observations exist; there are no measured lessons to promote yet.

## Revision history

- r1 2026-11-14: created from documented scope, historical handoff, local test
  inspection and external research. No prediction tested and no measured ascent
  return claimed. First implementation unit is the D2 corpus.
