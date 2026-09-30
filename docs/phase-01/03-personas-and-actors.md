# Personas, actors, and roles

## Target users

| User | Goals and pain points | Expected workflow and Renzai value |
|---|---|---|
| Software Developer | Integrate safeguards quickly; diagnose rejected traffic; avoid security expertise becoming a prerequisite. | Creates an application and key, calls analysis or gateway endpoints, inspects findings/logs, and uses the playground. |
| AI Engineer | Operate prompt/provider workflows safely while preserving model behavior and debugging context. | Configures environments and optional provider, tunes policies with analysts, reviews risk and output findings. |
| Security Engineer / Analyst | Detect, triage, and explain AI-specific abuse without opaque LLM-only decisions. | Reviews incidents, evidence, trends and policies; assigns, resolves, or marks false positives. |
| Startup or small engineering team | Gain practical controls with limited staff and a self-hosted option. | An owner sets up an organization, applications, privacy defaults, and lightweight alerting. |
| Open-source contributor | Understand intended behavior and contribute safely. | Uses requirements, stories, and traceability as a design baseline; proposes reviewed changes. |

## Application roles

Roles are organization-scoped. A user can have distinct roles in different organizations. Backend authorization MUST enforce all permissions; UI visibility is not authorization.

| Capability | Owner | Admin | Security Analyst | Developer | Viewer |
|---|:---:|:---:|:---:|:---:|:---:|
| View organization, applications, logs, dashboard | Yes | Yes | Yes | Yes | Yes |
| Create/update/archive applications and environments | Yes | Yes | No | Yes | No |
| Create, rotate, revoke application keys | Yes | Yes | No | Yes | No |
| Invite/remove members; change non-owner roles | Yes | Yes | No | No | No |
| Transfer ownership; delete organization; manage owners | Yes | No | No | No | No |
| Create/edit/enable policies | Yes | Yes | Yes | No | No |
| View/investigate/comment/assign incidents | Yes | Yes | Yes | View/comment | View |
| Resolve, ignore, or mark incidents false positive | Yes | Yes | Yes | No | No |
| Configure AI providers, retention, webhooks | Yes | Yes | No | No | No |
| View audit events | Yes | Yes | Yes | No | Yes |
| Manage personal account settings | Yes | Yes | Yes | Yes | Yes |

## Explicit decisions and open boundaries

An Owner may not remove or demote the last Owner. An Admin cannot perform ownership transfer or destructive organization operations. A Developer may comment on an incident only to add integration context and may not change its status or assignment. Whether Security Analysts may create webhooks is decided **No** for V1 because webhooks are operational integrations; the underlying webhook feature remains a V1 baseline only where scoped by FR-056. Fine-grained custom roles are out of scope for V1.
