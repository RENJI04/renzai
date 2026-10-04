# Phase 15A design QA

## Evidence

- Primary shell/dashboard reference: `exec-31c4c53e-ed4f-4e63-b705-c348f7ebc983.png`
- Incident/analyst reference: `exec-7ad6a470-4170-424e-b098-5efad0833cde.png`
- Playground reference: `exec-5f2e5681-1338-4bae-badc-262aa3a6824d.png`
- Implemented captures: `.reports/phase15a/*.png`
- Desktop viewport: 1280 x 720
- Mobile viewport: 390 x 844

## Comparison record

The implementation uses the first concept for the persistent shell, navigation,
dashboard hierarchy, cards, typography, and chart treatment. The second concept
specializes that foundation into a denser incident queue and investigation view,
with deterministic evidence kept visibly separate from violet, explicitly
advisory AI content. The third concept specializes the same tokens and controls
into the two-column Security Playground, with the authoritative action, risk,
findings, redaction, policy, and technical metadata prioritized.

Full-page captures were reviewed for login, registration, onboarding, dashboard,
playground, incidents, applications, policies, providers, analytics, AI
Intelligence, organization, and account security. Focused captures were also
reviewed for the dashboard, playground, and analyst workspace. The mobile shell
was checked with the navigation drawer open.

## Findings and fixes

- High: the original single-page console mixed overview, configuration,
  investigation, and account tasks. Fixed with a persistent shell and dedicated
  supported routes.
- High: deterministic evidence and AI advice competed visually. Fixed with
  separate regions, provenance labels, and a reserved violet advisory treatment.
- Medium: empty charts exposed meaningless axes. Fixed with contextual empty
  states while retaining real charts when the API supplies values.
- Medium: lower navigation items could start outside the sidebar viewport. Fixed
  by scrolling the active destination into view without moving keyboard focus.
- Medium: the Playwright host differed from the Next.js development origin,
  blocking hydration during the final run. Fixed by using `localhost` consistently.
- Low: animation made screenshot comparison nondeterministic. Recharts animation
  is disabled and CSS motion is short, purposeful, and removed under reduced
  motion.

No unresolved visual blocker remains. Realistic QA data is confined to Playwright
network fixtures and is not present in runtime product code.

final result: passed
