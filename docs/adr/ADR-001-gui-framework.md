# ADR-001: GUI framework — PySide6 with a map-renderer abstraction

Status: Accepted (user-approved 2026-08-01)

## Context
The game needs a desktop, dashboard-oriented GUI (tables, charts, docking,
map modes) on Linux and Windows. Candidates compared per specification §30:
PySide6, Pygame(-ce), Dear PyGui, and a hybrid (PySide6 + accelerated map).

## Decision
PySide6 (Qt 6, LGPL). The geographic map sits behind a small renderer
interface; the first implementation is QGraphicsView vector polygons with
choropleth modes. If profiling at grand-strategy scale demands it, an
OpenGL-accelerated renderer replaces the implementation behind the same
interface — the deferred half of the hybrid option.

## Rationale
Qt is best in class for exactly this UI shape (model/view tables over large
datasets, native docking, charts, mature threading integration, the only
realistic accessibility path). Pygame fails the dashboard requirement;
Dear PyGui trades polish, accessibility, and ecosystem depth for rendering
speed the MVP map does not need. PySide6 6.11.1 supports Python 3.14
(stable-ABI wheels, requires-python <3.15).

## Consequences
UI code lives in `polsim.ui` only; simulation stays headless (PySide6 is an
optional `ui` extra). Packaging uses PyInstaller later. A thin walking-
skeleton UI is inserted ~M2–M3 to de-risk Milestone 9.
