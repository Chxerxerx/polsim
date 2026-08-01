"""Immutable snapshot view-models crossing the simulation/UI boundary (M2.5).

Deliberately Qt-free: view-models are plain frozen dataclasses built inside
the simulation worker and handed to the UI thread, so the UI can only ever
render what a snapshot contains (design doc 01). The information-access
filter (specification section 25) will attach here once player roles exist.
"""

from __future__ import annotations

from dataclasses import dataclass

from polsim.core.seed import format_seed
from polsim.core.sim import Simulation


@dataclass(frozen=True)
class DistrictView:
    district_id: int
    name: str
    province_name: str
    population: int
    mean_income: float
    urban_share: float
    shape: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class WorldSnapshot:
    country_name: str
    seed_display: str
    week: int
    date_iso: str
    citizen_count: int
    represented_population: int
    map_width: float
    map_height: float
    districts: tuple[DistrictView, ...]

    def district(self, district_id: int) -> DistrictView | None:
        for view in self.districts:
            if view.district_id == district_id:
                return view
        return None


def build_snapshot(sim: Simulation) -> WorldSnapshot:
    """Build the current world snapshot from simulation state (worker side)."""
    populations = sim.aggregates.weighted_population()
    incomes = sim.aggregates.weighted_mean("income")
    urban_shares = sim.aggregates.weighted_mean("urban")
    province_names = {province.province_id: province.name for province in sim.world.provinces}
    districts = tuple(
        DistrictView(
            district_id=district.district_id,
            name=district.name,
            province_name=province_names[district.province_id],
            population=populations[district.district_id],
            mean_income=incomes[district.district_id],
            urban_share=urban_shares[district.district_id],
            shape=tuple(sim.world.district_shapes[district.district_id]),
        )
        for district in sim.world.districts
    )
    return WorldSnapshot(
        country_name=sim.world.country_name,
        seed_display=format_seed(sim.world_seed),
        week=sim.clock.week,
        date_iso=sim.clock.current_date.isoformat(),
        citizen_count=sim.population.count,
        represented_population=sim.aggregates.national_population(),
        map_width=sim.world.map_width,
        map_height=sim.world.map_height,
        districts=districts,
    )
