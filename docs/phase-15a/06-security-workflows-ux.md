# Security workflows UX

## Security Playground

The third design concept informs a flagship two-column workflow: editable test
content and scope on the left, authoritative security analysis on the right.
The API-provided action, risk score, severity, confidence, findings, categories,
risk contributions, policy rationale, redaction result, and version/timing
metadata retain their original semantics. The client does not recompute them.

## Incidents

The second concept informs the denser SOC workspace. Compact filters and queue
rows expose severity, status, scope, source, assignee, and time. The selected
incident organizes summary, evidence, timeline, assignment/status, comments, and
related analysis without changing the incident contract. Deterministic Security
Evidence is a primary region. AI-generated content appears in a separate violet
advisory region with task, state, provider/model, disclosure mode, provenance,
and result; it never implies that AI changed enforcement.

## Configuration

Applications now owns application creation, environments, and API keys.
Policies and Gateway providers have dedicated compact management surfaces. AI
Intelligence exposes the existing advisory provider configuration contract.
Credential-present state is displayed without revealing credentials; API-key
secrets remain a one-time response. Role-based control visibility is only an
affordance—the server remains authoritative.
