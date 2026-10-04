# Dashboard and analytics UX

The Dashboard is now a security overview based only on the existing Phase 10
response. It prioritizes requests, threats, blocked decisions, critical analyses,
open incidents, threat rate, time-bucket activity, risk distribution, threat
categories, policy actions, provider usage, and recent incidents. KPI cards show
labels, values, and context without fabricated trends.

Charts retain Recharts and the backend's metric semantics. Their axes, legends,
tooltips, typography, responsive sizing, and semantic colors are aligned with
the design system. Empty datasets render explanatory empty states instead of
large meaningless grids. Chart animation is disabled for deterministic evidence
and to avoid obscuring security values.

Analytics is a distinct exploration surface using the same response and
supported time, application, environment, and source filters. It emphasizes the
distribution, provider, and incident-state detail already present in the
contract; it introduces no client-side metric recomputation or query language.
