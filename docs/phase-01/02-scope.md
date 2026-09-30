# Scope management

## V1.0 scope

V1.0 is the planned first usable self-hosted product: account and organization management; role-based access; applications, environments and API keys; deterministic prompt and response analysis; explainable risk scoring; policy enforcement; incidents, logs, dashboard, and playground; optional OpenAI-compatible provider intelligence; gateway compatibility goal; audit events; privacy and retention controls; notifications; and documented health, readiness, and platform APIs.

## V1.1 candidate scope

- Slack, Discord, and email alerts
- Richer reports
- Additional provider adapters
- Plugin system
- Richer webhook management

## V2 candidate scope

- Deep GitHub integration and repository-aware incident context
- Analysis of AI-integration weaknesses and automatic patch suggestions
- Agent-runtime and multi-agent monitoring
- Tool-call authorization and approval workflow
- Advanced red-team assessment engine
- Kubernetes deployment and larger distributed deployment options

## Explicitly out of scope for V1

- Full SIEM, antivirus, endpoint detection, network IDS, or malware sandboxing
- Cloud security posture management or a Kubernetes security platform
- Generic full-source-code SAST or generic dependency scanning
- Enterprise billing and complex multi-region architecture

## Scope rules

V1.1 and V2 candidates are not V1 commitments. Adding any deferred item to V1 requires an explicit scope decision, corresponding requirements, and traceability updates. "Gateway compatibility" is a goal, not a promise of full provider-protocol parity until acceptance tests define the supported subset.
