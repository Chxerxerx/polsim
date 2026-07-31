# ADR-005: Default MVP scenario shape

Status: Accepted (user-approved 2026-08-01)

## Decision
The first fictional country: ~10,000,000 represented population (≈250,000
simulated citizens at population_weight ≈ 40; named characters weight 1);
one national parliament of 200 seats; election law = party-list proportional
representation, D'Hondt, multi-member districts, 4% national threshold.

## Rationale
List-PR with a threshold reliably yields multi-party parliaments, so the
MVP's coalition negotiation and PM selection (acceptance steps 12–17) occur
in normal play. FPTP as the default law would frequently produce
single-party majorities that bypass them. All five initial electoral systems
are still implemented and selectable through law.
