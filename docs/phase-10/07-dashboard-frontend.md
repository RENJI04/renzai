# Dashboard frontend

The Phase 10 dashboard is the first operational panel in the organization workspace. It provides KPI cards for analyses, threats, blocked decisions, critical analyses, open incidents, threat rate, and Gateway requests. Recharts renders activity, final-risk, threat-category, and policy-action charts; the chart bundle is loaded lazily.

Every chart has textual/table values available without relying on color. Provider usage and incident status use readable tables/lists, and the incident panel links to the existing Incident Queue. Responsive styles collapse filters, KPIs, and panels on narrow screens.

Pending queries render a skeleton rather than misleading zeros. A genuine zero result says “No security activity in this period.” API failures show only the stable safe message/request ID. No dashboard filter or result is written to localStorage, sessionStorage, cookies, or another browser cache. Parent keying and tenant-complete TanStack Query keys prevent stale cross-organization data.
