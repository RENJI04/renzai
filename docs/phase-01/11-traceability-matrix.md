# Initial traceability matrix

Verification identifiers are placeholders until implementation. Methods describe the planned evidence, not existing tests.

| User story | Functional requirements | Security requirements | Planned verification method |
|---|---|---|---|
| US-001 | FR-001–006 | SEC-001, 003, 017, 024 | Auth integration and security regression tests |
| US-002 | FR-007, 008, 012 | SEC-004 | Tenant API integration tests |
| US-003 | FR-009, 012, 047 | SEC-004, 015 | RBAC and audit integration tests |
| US-004 | FR-010–012 | SEC-004, 015 | Permission-matrix API tests |
| US-005 | FR-013, 014 | SEC-004 | Application lifecycle API tests |
| US-006 | FR-015–019 | SEC-002, 011, 018, 024 | Key lifecycle and secret-handling tests |
| US-007 | FR-020, 021, 041 | SEC-007, 016 | Analyze endpoint contract/performance tests |
| US-008 | FR-044–046 | SEC-007, 016, 020, 021 | Gateway compatibility and integration tests |
| US-009 | FR-022, 029, 030 | SEC-007 | Detector unit and regression corpus tests |
| US-010 | FR-023, 029, 030 | SEC-007 | Detector unit and regression corpus tests |
| US-011 | FR-025, 027, 028 | SEC-010, 023 | Output-analysis/redaction integration tests |
| US-012 | FR-031–033 | SEC-004, 015 | Policy ordering and authorization tests |
| US-013 | FR-032, 033, 045 | SEC-016 | Policy/gateway enforcement tests |
| US-014 | FR-028, 032, 033 | SEC-010, 023 | Redaction policy contract tests |
| US-015 | FR-034, 035, 047 | SEC-004, 015, 023 | Incident creation and audit tests |
| US-016 | FR-035, 036 | SEC-004 | Incident assignment authorization tests |
| US-017 | FR-035, 036, 047 | SEC-004, 015 | Incident state transition tests |
| US-018 | FR-039 | SEC-004, 023 | Dashboard data-isolation tests |
| US-019 | FR-037, 038 | SEC-004, 010, 023 | Log filter and isolation tests |
| US-020 | FR-040, 051, 052 | SEC-007, 010, 023 | Playground end-to-end and privacy tests |
| US-021 | FR-042 | SEC-012, 020, 021 | Provider config validation/security tests |
| US-022 | FR-041 | SEC-017 | No-provider integration test |
| US-023 | FR-046 | SEC-017, 021 | Provider failure and timeout tests |
| US-024 | FR-043 | SEC-012, 017 | Labelling and access integration tests |
| US-025 | FR-047, 048 | SEC-015, 023 | Append-only audit contract tests |
| US-026 | FR-051–053 | SEC-010, 023 | Privacy/retention integration tests |
| US-027 | FR-017–019 | SEC-002, 011, 018 | Key revocation/rotation tests |
| US-028 | FR-024, 029, 030 | SEC-007 | Obfuscation-detector unit and regression corpus tests |
| US-029 | FR-026, 029, 030 | SEC-007 | Threat-indicator unit and policy integration tests |
| US-030 | FR-049 | SEC-004, 023 | Notification authorization and isolation tests |
| US-031 | FR-050, 056 | SEC-004, 015, 019–022 | Webhook lifecycle, signature, replay, and SSRF tests |
| US-032 | FR-054, 055 | SEC-017 | API-documentation and operational-endpoint contract tests |
