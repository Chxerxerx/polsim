"""Milestone 0 smoke test: the package imports and declares a version.

Real system tests begin in Milestone 1 (see docs/design/05-testing.md).
"""

import polsim


def test_package_imports_and_has_version() -> None:
    assert isinstance(polsim.__version__, str)
    assert polsim.__version__
