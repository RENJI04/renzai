# Design system

Renzai now uses a dark-first operational system built from near-black, deep navy,
slate, cool-gray text, and a restrained mint/cyan brand accent. Semantic colors
have fixed jobs: green for safe/success, amber for review, red for blocked or
critical conditions, violet for AI-generated advisory material, and cyan for
neutral information.

The first supplied concept defines the visual foundation: shell proportions,
navigation language, typography, spacing, dashboard hierarchy, cards, charts,
buttons, inputs, badges, tables, and status feedback. The incident and playground
concepts specialize those same rules rather than introducing separate themes.

Global CSS variables centralize surfaces, borders, radius, shadows, type color,
semantic accents, and motion timing. Controls share consistent height, focus
rings, disabled treatment, and immediate hover/pressed feedback. Cards use
restrained borders and depth; denser operational tables avoid unnecessary nested
panels. Technical identifiers use the system monospace stack.

Reusable structure is concentrated in `WorkspaceShell`, page headers, KPI cards,
empty/loading/error treatments, badges, filter bars, tables, and the existing
feature consoles. CSS/native transitions are used instead of adding a motion
library.
