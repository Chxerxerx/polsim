# 02 — Data Model

## Entity identifiers

Stable 64-bit integer IDs, unique per entity domain (CitizenId, PartyId,
DistrictId, EventId, ...) wrapped in distinct types for mypy-strict safety.
IDs are permanent across save/load and never reused within a world.

## Population (struct-of-arrays)

Ordinary citizens are rows in a columnar store: one NumPy array per
attribute, citizens addressed by index, with a stable CitizenId ↔ index map.
Column dtypes are chosen per attribute (float32 for continuous traits, int8
for enumerations, int32 for references). Approximate scale: ~100 columns ×
250k rows × ≤4 B ≈ ≤100 MB.

Core column groups (from specification §6.2): identity & demographics (age,
sex, gender, sexuality, ethnicity, culture, language, religion), socioeconomy
(occupation, employment, income, wealth, savings, property, education,
class, housing), geography (town, district, province, urban/rural),
civic status (citizenship, military service), politics (ideology-axis
positions, per-issue opinions, party loyalty per party, institutional trust,
political knowledge, engagement, turnout propensity), and life-simulation
hooks (health, family links, life events).

`population_weight` is a per-citizen integer; named characters always have
weight 1. Weighted citizens are persistent individual agents — voting is
never reduced to demographic percentages.

## Named characters

Politicians, candidates, ministers, judges, journalists, and other
politically significant people are rich Python objects layered *on top of*
a population row (they also exist in the columnar store), carrying skills,
relationships, offices, schedules, and full memory objects.

## Citizen memory

A global append-only event log stores politically relevant events once
(promises, scandals, laws, economic shocks, local events...). Each ordinary
citizen holds a small fixed-width array of (EventId, salience:float16)
pairs; salience decays in batch and campaigns modify salience (redirect
attention, dispute allegations) rather than deleting entries, so memories
never simply vanish. Named characters keep unbounded structured memories.

## Political entities

Parties, branches, factions, and organizations are ordinary relational
entities (members, leaders, budgets, rules, endorsements) referencing
citizens/characters by ID. Faction membership constraints (no directly
contradictory factions) are validated at join time.

## Laws and election law

Every law = structured mechanical components (typed parameters the
simulation reads) + generated descriptive text for the player. Election law
is one law domain: districts, magnitudes, formula, thresholds, eligibility,
turnout rules, recount rules — all data, interpreted by the `elections`
engine. Mechanics never depend on natural-language interpretation.

## Persistence mapping (ADR-002)

Single SQLite file (WAL): relational tables for entities, relations, laws,
history, and the event log; population columns as zstd-compressed NumPy
chunk blobs partitioned by district with dirty-chunk incremental saves;
`schema_version` + stepwise migrations; seed and action log retained for
deterministic replay; per-chunk checksums plus SQLite integrity checks.
