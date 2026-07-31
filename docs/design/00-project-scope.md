# 00 — Project Scope (Design Document)

Source of requirements: the master development prompt (referred to below as
"the specification"). This document condenses scope; it does not replace the
specification.

## Vision

A turn-based political simulator (1 turn = 1 week) in which the player rises
from an unimportant political character toward party leadership, parliament,
ministries, and government leadership, with grand-strategy systems (economy,
diplomacy, war) added long after the MVP. Democratic, authoritarian,
monarchical, revolutionary, and other routes must all be viable; the game
models consequences without assigning a universal moral score.

## MVP (election-focused)

One fictional, isolated, modern parliamentary republic. The player selects or
creates a party, campaigns nationally and by district through weekly schedule
slots (with imperfect delegation to staff), reads uncertain polling, competes
against AI parties operating under identical rules, and contests a national
election in which every simulated citizen makes an individual weighted voting
decision. Seats are allocated under configurable, data-driven election law.
The player then negotiates coalitions, supports or selects a prime minister,
and continues play in government or opposition. Save/load and same-seed
determinism must not change outcomes. Acceptance criteria: specification §35.

## Default MVP scenario (approved 2026-08-01, ADR-005)

- Represented population: ~10,000,000 (≈ 250,000 simulated citizens at
  population_weight ≈ 40; named characters have weight 1).
- Unicameral parliament, 200 seats.
- Election law of the land: party-list proportional representation, D'Hondt,
  multi-member districts, 4% national threshold. (All five initial electoral
  systems are implemented and selectable through law; this is merely the
  default country's law.)

## MVP non-goals (explicitly deferred)

Legislation/lawmaking depth, ministries, judiciary, economy, media depth
beyond campaign needs, corruption/political crime, historical eras, real and
procedural countries, international politics, war, and modding APIs. Core
systems must be designed so these can be added without rewrites, but they are
not implemented in the MVP.

## Hard constraints

Python 3.14 primary (ADR-003); Linux first, Windows a goal; offline; no paid
APIs; strict simulation/UI separation; determinism from a visible, shareable
seed; no hidden AI bonuses; role-based information access (fog of politics);
no fake gameplay placeholders presented to the player; no universal moral
score.
