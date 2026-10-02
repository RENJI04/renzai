# Phase 11 scope

Phase 11 implements optional, advisory AI assistance for incident triage under FR-041 and FR-043. It adds dedicated OpenAI-compatible AI provider configuration, asynchronous incident-analysis requests, validated results, and a labelled Incident Detail panel.

Detectors, risk scoring, policy evaluation, and Gateway enforcement remain authoritative. Analyze and Gateway do not import or invoke the AI intelligence module. Phase 11 does not add tools, autonomous actions, policy activation, detector changes, embeddings, arbitrary prompts, streaming, notifications, webhooks, SDKs, or Phase 12 capabilities.

Phase 3 defines only incident explanation requests; it does not define a similar-incidents API. Similar-incident assistance is therefore deferred rather than guessed.
