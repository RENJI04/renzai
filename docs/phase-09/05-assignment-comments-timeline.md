# Assignment, comments, and timeline

Assignment accepts an active Owner, Admin, or Security Analyst membership in the same organization. Assign and unassign increment the incident version and append both an operator timeline entry and an organization audit event. Foreign, inactive, disabled, and ineligible users are hidden with `not_found_or_hidden`.

Comments are immutable, bounded to 4,000 characters, and treated as plain text. Control characters are rejected. React renders the value as text; there is no Markdown or HTML execution. Comment bodies appear only in the comment collection; timeline and audit metadata reference the comment ID and never duplicate its body.

The append-style timeline records incident creation, policy action, status change, assignment/unassignment, comment addition, and false-positive marking. The schema also permits `related_event_added` for a future explicit relation-add operation; Phase 9 does not automatically merge unrelated events or expose an attach API. Entries include a safe summary, actor/service identity, correlation ID, safe allowlisted metadata, and optional event/policy references. Automatic Gateway creation uses timeline/security history without tenant-audit spam; operator mutations use `AuditEvent`.
