"""Repository guard: uncontrolled randomness is forbidden in simulation code.

Enforces design doc 03: the standard ``random`` module is banned everywhere
under ``src/polsim``; *using* NumPy's ``random`` namespace (module-level
draws, ``default_rng``) is allowed only in ``core/rng.py``, while pure type
references (``np.random.Generator``/``SeedSequence``/``Philox``) are fine
everywhere since Generators are injected by ``RngManager``; OS entropy
(``secrets``, ``os.urandom``) only in ``core/seed.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "polsim"

_ALLOWED_NP_RANDOM_TYPES = frozenset({"Generator", "SeedSequence", "Philox", "BitGenerator"})


def _violations() -> list[str]:
    problems: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        parents = {
            child: parent
            for parent in ast.walk(tree)
            for child in ast.iter_child_nodes(parent)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root == "random":
                        problems.append(f"{rel}:{node.lineno} imports random")
                    if root == "secrets" and rel != "core/seed.py":
                        problems.append(f"{rel}:{node.lineno} imports secrets")
            if isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root == "random":
                    problems.append(f"{rel}:{node.lineno} imports from random")
                if root == "secrets" and rel != "core/seed.py":
                    problems.append(f"{rel}:{node.lineno} imports from secrets")
            if isinstance(node, ast.Attribute):
                value = node.value
                numpy_random = (
                    isinstance(value, ast.Name)
                    and value.id in ("np", "numpy")
                    and node.attr == "random"
                )
                if numpy_random and rel != "core/rng.py":
                    parent = parents.get(node)
                    type_reference = (
                        isinstance(parent, ast.Attribute)
                        and parent.attr in _ALLOWED_NP_RANDOM_TYPES
                    )
                    if not type_reference:
                        problems.append(f"{rel}:{node.lineno} uses numpy.random")
                if node.attr == "urandom" and rel != "core/seed.py":
                    problems.append(f"{rel}:{node.lineno} uses os.urandom")
    return problems


def test_no_uncontrolled_randomness_in_simulation_code() -> None:
    assert _violations() == []
