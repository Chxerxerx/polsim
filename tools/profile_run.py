"""Profiling infrastructure (Milestone 1).

Profile a scripted simulation run and print the hottest call sites:

    python tools/profile_run.py --weeks 500 --seed 42
"""

from __future__ import annotations

import argparse
import cProfile
import pstats

from polsim.core.log import setup_logging
from polsim.core.sim import Simulation


def _run(weeks: int, seed: int) -> None:
    sim = Simulation.new_game(world_seed=seed)
    for _ in range(weeks):
        sim.rng.stream("profile.demo").integers(0, 1000, size=64)
        sim.advance_week()
    sim.state_hash()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weeks", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--top", type=int, default=25)
    args = parser.parse_args()

    setup_logging("WARNING")
    profiler = cProfile.Profile()
    profiler.enable()
    _run(args.weeks, args.seed)
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats(pstats.SortKey.CUMULATIVE).print_stats(args.top)


if __name__ == "__main__":
    main()
