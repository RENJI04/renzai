# Information architecture

The implemented navigation mirrors supported backend capabilities:

| Group | Surface | Route |
| --- | --- | --- |
| Overview | Security overview | `/dashboard` |
| Security | Security Playground | `/playground` |
| Security | Incidents and analyst workspace | `/incidents` |
| Security | Policies | `/policies` |
| Infrastructure | Applications, environments, and API keys | `/applications` |
| Infrastructure | Gateway providers | `/providers` |
| Intelligence | Analytics | `/analytics` |
| Intelligence | AI Intelligence configurations | `/ai-intelligence` |
| Organization | Organization and invitations | `/organization` |
| Organization | Account & Security | `/account` |

The root route remains valid and presents authentication, onboarding, or the
overview according to session and organization state. Existing APIs do not
require fabricated dynamic detail routes: application resources stay together
on the Applications surface, while incident queue and selected detail coexist in
one analyst workspace. This preserves deep-link behavior that actually exists
and avoids advertising unsupported pages.

Dashboard contains only overview information. Configuration, incident actions,
AI configuration, organization operations, and account security have dedicated
surfaces.
