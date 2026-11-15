# Support and release policy

load-clean is pre-1.0 software. It does not promise API compatibility, active
maintenance, a security response deadline, or a support SLA. Use issue reports
and reproducible examples to document problems; a report does not guarantee a
fix or response.

CI tests Python 3.10, 3.11, 3.12, 3.13, and 3.14. Other Python versions and
platforms may work but are not covered by this matrix. CI also builds a wheel
and checks core imports and CLI help in an isolated environment without IPython.

A release tag must exactly match `v` followed by the version in `pyproject.toml`.
Release artifacts are attached to a GitHub release only after the test matrix
and wheel build succeed. This workflow does not publish to PyPI.

To prepare a release, update `project.version` in `pyproject.toml`, build and
verify the wheel and source distribution, and commit the version change. Push
the commit and a matching `vVERSION` tag (for example, `v0.0.3`). Confirm that
the tag's CI run succeeds and the GitHub release includes both distributions.
Use a new version and tag when correcting a release; do not move published tags.

Generated Python and notebook execution have the same trust requirements as
running the original project code. Use trusted source files and review exports;
this package is not a sandbox.
