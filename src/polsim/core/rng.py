"""Deterministic named random-number streams (Milestone 1).

All simulation randomness flows through named substreams derived from the
world seed (design doc 03). Stream keys are derived by hashing the stream
name, so adding new streams never disturbs existing ones. Simulation code
must never use the standard ``random`` module or NumPy's module-level
randomness; a repository guard test enforces this.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

import numpy as np

MAX_SEED = 2**64 - 1


def _stream_entropy(world_seed: int, name: str) -> np.random.SeedSequence:
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return np.random.SeedSequence([world_seed, int.from_bytes(digest, "little")])


def _encode(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return {"__ndarray__": obj.tolist(), "dtype": str(obj.dtype)}
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, dict):
        return {key: _encode(value) for key, value in obj.items()}
    return obj


def _decode(obj: Any) -> Any:
    if isinstance(obj, dict):
        if "__ndarray__" in obj:
            return np.asarray(obj["__ndarray__"], dtype=obj["dtype"])
        return {key: _decode(value) for key, value in obj.items()}
    return obj


class RngManager:
    """Creates, caches, serializes, and restores named Philox streams."""

    def __init__(self, world_seed: int) -> None:
        if not 0 <= world_seed <= MAX_SEED:
            raise ValueError("world seed must fit in an unsigned 64-bit integer")
        self.world_seed = world_seed
        self._streams: dict[str, np.random.Generator] = {}

    def stream(self, name: str) -> np.random.Generator:
        """Return the named stream, creating it deterministically on first use."""
        generator = self._streams.get(name)
        if generator is None:
            bit_generator = np.random.Philox(seed=_stream_entropy(self.world_seed, name))
            generator = np.random.Generator(bit_generator)
            self._streams[name] = generator
        return generator

    def snapshot(self) -> dict[str, str]:
        return {
            name: json.dumps(_encode(generator.bit_generator.state), sort_keys=True)
            for name, generator in sorted(self._streams.items())
        }

    def restore(self, states: Mapping[str, str]) -> None:
        self._streams.clear()
        for name in sorted(states):
            generator = self.stream(name)
            generator.bit_generator.state = _decode(json.loads(states[name]))
