# Navigation and onboarding

The persistent shell provides canonical branding, grouped navigation, active
state, organization context, operational state, account entry, and sign-out. A
compact top bar reinforces the current page context. On smaller screens the
sidebar becomes a keyboard-accessible drawer with an explicit open/close control.
The active destination is scrolled into view when necessary.

Authentication uses the official Renzai identity in a restrained split layout.
Login, registration, and password reset retain visible labels, validation,
loading/submit state, safe errors, request IDs, and existing session semantics.
No unsupported identity claim or MFA feature was added.

First-run onboarding explains the organization isolation boundary and presents
the existing organization creation and invitation acceptance operations as a
guided start. Once an organization exists, the Applications surface exposes the
supported application, environment, and API-key progression. One-time API-key
reveal behavior is preserved.
