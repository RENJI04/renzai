# V1 route and operation catalog

This is a design contract, not implemented FastAPI code. Renzai management APIs use `/api/v1`; the limited Gateway route is `/v1/chat/completions`. Request/response field names are `snake_case`. All responses have `request_id` (header or error body), and all writes use optimistic version or conflict handling where stated. `Page<T>` means cursor pagination defined below.

## Table conventions

`P` = public/token flow; `S` = opaque browser session with CSRF for writes; `K` = environment-scoped application key. Roles: `operator` = Owner/Admin; `app_editor` = Owner/Admin/Developer; `policy_editor` = Owner/Admin/Security Analyst; `incident_editor` = Owner/Admin/Security Analyst; `playground_user` = Owner/Admin/Security Analyst/Developer; `reader` = any organization role; `audit_reader` = Owner/Admin/Security Analyst/Viewer; `self` = authenticated user. `org`, `app`, `env`, `incident`, `recipient` in Access are server-validated scope, never authority from a path ID alone. `E0` = `validation|rate_limit|internal_error`; `ES` = E0 plus `authentication|authorization|not_found_or_hidden`; `EK` = E0 plus `authentication|not_found_or_hidden`. Cells add operation-specific errors. `Audit` names the successful security action; `—` means no required audit event (security request/event logging may still apply). `Idem`: `read` = naturally safe GET; `yes` = supported bounded `Idempotency-Key`; `no-replay` = a one-time secret/link is not replayable; `state` = repeat to desired state is idempotent; `—` = no client idempotency contract. Rate classes are defined in [configuration](19-configuration-contracts.md).

## Authentication and tenancy

| Method and route | Purpose | Access | Request → response shape | Major errors | Audit | Rate | Idem |
|---|---|---|---|---|---|---|---|
| POST `/api/v1/auth/register` | Create account | P, global | email,password → UserSummary/verification_state | E0, conflict | account_registered | AUTH_STRICT | — |
| POST `/api/v1/auth/login` | Establish session | P, global | email,password → SessionBootstrap + cookie | E0, authentication | login_success/failure safe event | AUTH_STRICT | — |
| POST `/api/v1/auth/logout` | Revoke current session | S self | empty → acknowledgement + cleared cookie | ES | session_revoked | SESSION | state |
| POST `/api/v1/auth/password/change` | Rotate password/session | S self | current_password,new_password → acknowledgement/new session | ES, conflict | password_changed | AUTH_STRICT | — |
| POST `/api/v1/auth/password/reset/request` | Issue reset flow | P, global | email → uniform acknowledgement | E0 | reset_requested safe event | PASSWORD_RESET | — |
| POST `/api/v1/auth/password/reset/confirm` | Consume reset token | P, global | token,new_password → acknowledgement | E0, authentication | password_reset | PASSWORD_RESET | state |
| POST `/api/v1/auth/email/verification/request` | Optional verification flow | S self | empty → uniform acknowledgement | ES, configuration_error | verification_requested | PASSWORD_RESET | — |
| POST `/api/v1/auth/email/verification/confirm` | Redeem verification token | P, global | token → acknowledgement | E0, authentication | email_verified | PASSWORD_RESET | state |
| GET `/api/v1/auth/session` | Bootstrap user/session/CSRF | S self | empty → UserSummary, memberships, csrf_token, expiry | ES | — | SESSION | read |
| POST `/api/v1/organizations` | Create tenant | S self | name,slug → OrganizationSummary | ES, conflict | organization_created | ADMIN | yes |
| GET `/api/v1/organizations` | List own tenants | S self | cursor,limit → Page<OrganizationSummary> | ES | — | SESSION | read |
| GET `/api/v1/organizations/{id}` | Read tenant settings | S reader, org | id → OrganizationDetail | ES | — | SESSION | read |
| PATCH `/api/v1/organizations/{id}` | Update settings | S operator, org | name,settings,version → OrganizationDetail | ES, conflict | organization_updated | ADMIN | — |
| GET `/api/v1/organizations/{org}/members` | List members | S reader, org | cursor,limit → Page<MemberSummary> | ES | — | SESSION | read |
| POST `/api/v1/organizations/{org}/invitations` | Issue time-bounded link | S operator, org | email,role,expires_at? → InvitationIssued (link once) | ES, conflict | invitation_created | ADMIN | no-replay |
| POST `/api/v1/invitations/{token}/accept` | Accept invitation | P/token, token tenant | token plus authenticated/registration identity proof → MembershipSummary | E0, authentication, conflict | invitation_accepted | AUTH_STRICT | state |
| PATCH `/api/v1/organizations/{org}/members/{member}` | Change non-owner role | S operator, org/member | role,version → MemberSummary | ES, conflict | member_role_changed | ADMIN | — |
| DELETE `/api/v1/organizations/{org}/members/{member}` | Remove member | S operator, org/member | empty → acknowledgement | ES, conflict | member_removed | ADMIN | state |

Invitation token path segments are redacted from access logs, are never used in redirect URLs, and are consumed once. Ownership transfer/deletion is reserved for an explicitly reviewed future contract; these routes cannot perform owner-only destructive actions implicitly.

## Applications, environments and keys

| Method and route | Purpose | Access | Request → response shape | Major errors | Audit | Rate | Idem |
|---|---|---|---|---|---|---|---|
| POST `/api/v1/organizations/{org}/applications` | Create app | S app_editor, org | name,privacy? → ApplicationDetail | ES, conflict | application_created | ADMIN | yes |
| GET `/api/v1/organizations/{org}/applications` | List apps | S reader, org | cursor,limit,status → Page<ApplicationSummary> | ES | — | SESSION | read |
| GET `/api/v1/organizations/{org}/applications/{app}` | Read app | S reader, org/app | ids → ApplicationDetail | ES | — | SESSION | read |
| PATCH `/api/v1/organizations/{org}/applications/{app}` | Update app/privacy | S app_editor for name; operator for privacy, org/app | name?,privacy?,retention?,version → ApplicationDetail | ES, conflict | application_or_privacy_changed | ADMIN | — |
| POST `/api/v1/organizations/{org}/applications/{app}/archive` | Archive app | S app_editor, org/app | version → ApplicationDetail | ES, conflict | application_archived | ADMIN | state |
| POST `/api/v1/organizations/{org}/applications/{app}/environments` | Create environment | S app_editor, org/app | type,config? → EnvironmentDetail | ES, conflict | environment_created | ADMIN | yes |
| GET `/api/v1/organizations/{org}/applications/{app}/environments` | List environments | S reader, org/app | cursor,limit → Page<EnvironmentDetail> | ES | — | SESSION | read |
| PATCH `/api/v1/organizations/{org}/applications/{app}/environments/{env}` | Update environment | S app_editor for label; operator for fail-safe/provider, org/app/env | config,version → EnvironmentDetail | ES, conflict | environment_changed | ADMIN | — |
| POST `/api/v1/organizations/{org}/applications/{app}/environments/{env}/keys` | Issue key once | S app_editor, org/app/env | label,expires_at? → KeyIssued{secret_once,metadata} | ES, conflict | key_created | ADMIN | no-replay |
| GET `/api/v1/organizations/{org}/applications/{app}/environments/{env}/keys` | List key metadata | S app_editor, org/app/env | cursor,limit → Page<KeyMetadata> | ES | — | SESSION | read |
| POST `/api/v1/organizations/{org}/applications/{app}/environments/{env}/keys/{key}/revoke` | Revoke key | S app_editor, org/app/env/key | empty → KeyMetadata | ES | key_revoked | ADMIN | state |
| POST `/api/v1/organizations/{org}/applications/{app}/environments/{env}/keys/{key}/rotate` | Replace/revoke key | S app_editor, org/app/env/key | expires_at? → KeyIssued{secret_once,metadata} | ES, conflict | key_rotated | ADMIN | no-replay |

Privacy/retention mutations under application update require operator permission even though Developers may edit the application name. Server checks fields independently, not just route-level role.

## Security, policies and incidents

| Method and route | Purpose | Access | Request → response shape | Major errors | Audit | Rate | Idem |
|---|---|---|---|---|---|---|---|
| POST `/api/v1/analyze` | Analyze bounded content | K, env from key | direction,content,metadata? → AnalysisResult | EK, inspection_failure | security event | ANALYZE | — |
| POST `/api/v1/organizations/{org}/playground/analyze` | Manual analysis | S playground_user, org/app/env selected | app,env,direction,content → AnalysisResult | ES, inspection_failure | security event | ANALYZE | — |
| POST `/api/v1/organizations/{org}/policies` | Create policy identity/version | S policy_editor, org/scope | scope,phase,priority,conditions,action → PolicyDetail | ES, conflict | policy_created | ADMIN | yes |
| GET `/api/v1/organizations/{org}/policies` | List policy identities | S reader, org | scope,phase,enabled,cursor,limit → Page<PolicySummary> | ES | — | SESSION | read |
| GET `/api/v1/organizations/{org}/policies/{policy}` | Read policy/version | S reader, org/policy | version? → PolicyDetail | ES | — | SESSION | read |
| PATCH `/api/v1/organizations/{org}/policies/{policy}` | Create new immutable version | S policy_editor, org/policy | condition/action/priority changes,expected_version → PolicyDetail | ES, conflict | policy_version_created | ADMIN | — |
| POST `/api/v1/organizations/{org}/policies/{policy}/enable` | Activate policy | S policy_editor, org/policy | version,expected_version → PolicyDetail | ES, conflict | policy_enabled | ADMIN | state |
| POST `/api/v1/organizations/{org}/policies/{policy}/disable` | Disable policy | S policy_editor, org/policy | expected_version → PolicyDetail | ES, conflict | policy_disabled | ADMIN | state |
| GET `/api/v1/organizations/{org}/policies/{policy}/versions` | Inspect history | S reader, org/policy | cursor,limit → Page<PolicyVersion> | ES | — | SESSION | read |
| POST `/api/v1/organizations/{org}/policies/{policy}/rollback` | Reactivate old version | S policy_editor, org/policy | version,expected_version → PolicyDetail | ES, conflict | policy_rolled_back | ADMIN | — |
| POST `/api/v1/organizations/{org}/policies/preview` | Preview effective action | S policy_editor, org/app/env | scope,phase,facts,proposed_version? → PolicyDecisionPreview | ES, validation | — | ADMIN | — |
| GET `/api/v1/organizations/{org}/incidents` | List incidents | S reader, org | filters,cursor,limit → Page<IncidentSummary> | ES | — | SESSION | read |
| GET `/api/v1/organizations/{org}/incidents/{incident}` | Investigate detail/timeline | S reader, org/incident | id → IncidentDetail | ES | — | SESSION | read |
| POST `/api/v1/organizations/{org}/incidents` | Create manual incident | S incident_editor, org/app/env | title,severity,context → IncidentDetail | ES, conflict | incident_created | ADMIN | yes |
| PATCH `/api/v1/organizations/{org}/incidents/{incident}/status` | Transition status | S incident_editor, org/incident | status,reason,version → IncidentDetail | ES, conflict | incident_status_changed | ADMIN | — |
| PATCH `/api/v1/organizations/{org}/incidents/{incident}/assignment` | Assign member | S incident_editor, org/incident/member | assignee_user_id,version → IncidentDetail | ES, conflict | incident_assigned | ADMIN | — |
| POST `/api/v1/organizations/{org}/incidents/{incident}/comments` | Add context | S Owner/Admin/Analyst/Developer, org/incident | body → IncidentComment | ES, validation | incident_comment_added | ADMIN | — |
| GET `/api/v1/organizations/{org}/events` | Search privacy-filtered logs | S reader, org | app,env,severity,threat,action,time,cursor,limit → Page<SecurityEventSummary> | ES | — | SESSION | read |
| GET `/api/v1/organizations/{org}/events/{event}` | Inspect permitted event | S reader, org/event | id → SecurityEventDetail by storage mode | ES | — | SESSION | read |
| POST `/api/v1/organizations/{org}/incidents/{incident}/ai-analysis` | Request optional explanation | S incident_editor, org/incident | analysis_kind → AIAnalysisRequest | ES, configuration_error | ai_analysis_requested | ADMIN | yes |
| GET `/api/v1/organizations/{org}/ai-analysis/{request}` | Read labelled status/result | S reader, org/request | id → AIAnalysisStatus/Result | ES | — | SESSION | read |

Policy preview accepts only synthetic/authorized safe facts and never executes arbitrary scripts. Incident and event detail responses respect privacy mode and content expiry. An AI result is always labelled `ai_generated` and remains separate from deterministic findings.

## Providers, notifications, audit and analytics

| Method and route | Purpose | Access | Request → response shape | Major errors | Audit | Rate | Idem |
|---|---|---|---|---|---|---|---|
| POST `/api/v1/organizations/{org}/providers` | Configure provider | S operator, org | name,kind,url,model,key?,timeouts → ProviderSafeDetail | ES, conflict, configuration_error | provider_created | ADMIN | — |
| GET `/api/v1/organizations/{org}/providers` | List masked providers | S reader, org | cursor,limit → Page<ProviderSafeSummary> | ES | — | SESSION | read |
| GET `/api/v1/organizations/{org}/providers/{provider}` | Read masked config | S reader, org/provider | id → ProviderSafeDetail | ES | — | SESSION | read |
| PATCH `/api/v1/organizations/{org}/providers/{provider}` | Update/rotate config | S operator, org/provider | safe fields,key replacement?,version → ProviderSafeDetail | ES, conflict, configuration_error | provider_changed | ADMIN | — |
| POST `/api/v1/organizations/{org}/providers/{provider}/validate` | Validate outbound target/health | S operator, org/provider | empty → ValidationStatus | ES, provider_timeout, provider_error | provider_validation_requested | ADMIN | — |
| DELETE `/api/v1/organizations/{org}/providers/{provider}` | Disable/delete config | S operator, org/provider | empty → acknowledgement | ES, conflict | provider_deleted | ADMIN | state |
| GET `/api/v1/organizations/{org}/notifications` | List own in-app items | S self, org/recipient | unread?,cursor,limit → Page<Notification> | ES | — | SESSION | read |
| POST `/api/v1/organizations/{org}/notifications/{notification}/read` | Mark own item read | S self, org/recipient | empty → Notification | ES | — | SESSION | state |
| POST `/api/v1/organizations/{org}/webhooks` | Create signed destination | S operator, org | name,url,event_types → DestinationIssued{signing_secret_once,metadata} | ES, conflict, configuration_error | webhook_created | ADMIN | no-replay |
| GET `/api/v1/organizations/{org}/webhooks` | List destinations | S operator, org | cursor,limit → Page<WebhookSafeSummary> | ES | — | SESSION | read |
| PATCH `/api/v1/organizations/{org}/webhooks/{destination}` | Update destination | S operator, org/destination | safe fields,version → WebhookSafeDetail | ES, conflict, configuration_error | webhook_changed | ADMIN | — |
| POST `/api/v1/organizations/{org}/webhooks/{destination}/enable` | Enable destination | S operator, org/destination | version → WebhookSafeDetail | ES, conflict | webhook_enabled | ADMIN | state |
| POST `/api/v1/organizations/{org}/webhooks/{destination}/disable` | Disable destination | S operator, org/destination | version → WebhookSafeDetail | ES | webhook_disabled | ADMIN | state |
| DELETE `/api/v1/organizations/{org}/webhooks/{destination}` | Delete destination | S operator, org/destination | empty → acknowledgement | ES | webhook_deleted | ADMIN | state |
| POST `/api/v1/organizations/{org}/webhooks/{destination}/test` | Send safe synthetic test | S operator, org/destination | empty → DeliveryStatus | ES, provider_timeout, provider_error | webhook_test_requested | WEBHOOK_TEST | yes |
| GET `/api/v1/organizations/{org}/audit` | Search audit records | S audit_reader, org | actor,action,resource,time,cursor,limit → Page<AuditEvent> | ES | — | SESSION | read |
| GET `/api/v1/organizations/{org}/analytics/dashboard` | Dashboard counts/series | S reader, org | app,env,time_range → DashboardSummary/series | ES | — | SESSION | read |

Webhook management stays Owner/Admin only; Security Analysts cannot create destinations. Provider and webhook read responses mask secret material. Synthetic webhook tests never include real prompts.

## Operations and Gateway

| Method and route | Purpose | Access | Request → response shape | Major errors | Audit | Rate | Idem |
|---|---|---|---|---|---|---|---|
| GET `/health` | Process liveness | P, no tenant | empty → `{status:"alive"}` | internal_error | — | edge limit | read |
| GET `/ready` | Safe traffic readiness | P/probe, no tenant | empty → `{status:"ready"}` or minimal 503 | configuration_error, internal_error | — | edge limit | read |
| POST `/v1/chat/completions` | Limited secured completion | K, env from key | allowlisted chat request → checked completion or Renzai error | EK, policy_block, review_required, provider_timeout, provider_error, inspection_failure, configuration_error | security event | GATEWAY | — |

## Pagination, filters and versioning

Lists use `limit` default 50/max 100 and an opaque signed cursor bound to tenant, filters and `(created_at DESC,id DESC)` ordering. A changed filter invalidates the cursor with `validation`; cursors are not authorization. Time filters use UTC RFC 3339 `from`/`to` and a bounded maximum window. Named filters only; no SQL-like expressions. `GET /health` reports process liveness even when stores are down. `GET /ready` is 200 only when required secure traffic can be served; Redis loss makes protected auth/Analyze/Gateway/admin writes unavailable and readiness 503 by default, while some read-only paths may work. Public bodies do not reveal internal topology. OpenAPI documents implemented V1 routes and the common [error envelope](17-error-contracts.md).
