# Risk contributions

Every finding receives a persisted contribution containing its finding reference, category, detector/version, profile base weight, confidence, integer raw contribution, overlap group, retained/suppressed state, suppressor, corroboration allocation, and critical-floor marker.

Suppressed records remain available for reconstruction but are never counted. Response explanations expose only safe identifiers and arithmetic; matched text, secrets, and original content are excluded. Contributions, findings, the result, event, and policy decision commit atomically.

Spanless evidence follows the conservative Phase 3 grouping rule. Equivalent evidence is not double-counted, same-category evidence does not corroborate, and a third finding never adds score.
