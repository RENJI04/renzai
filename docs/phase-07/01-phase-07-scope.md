# Phase 7 scope

Phase 7 implements deterministic V1 risk scoring and tenant-scoped policy evaluation for Analyze and the Security Playground. It adds immutable risk/policy versions, explainable contributions, explicit baseline policies, atomic decisions, management APIs, and practical policy UI.

The pipeline is authenticate → limit → validate → normalize → detect/aggregate → risk → policy → action/redaction → privacy filter → atomic persistence → response. Risk and policy domains are pure and perform no I/O.

Gateway/provider execution, credentials, incidents, notifications, webhooks, AI intelligence, analytics, SDKs, tools, and approval workflows remain out of scope. `block` and `require_review` are successful Analyze results, not transport failures.
