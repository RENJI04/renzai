"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AppWindowIcon, FlaskIcon, KeyIcon, ShieldCheckIcon } from "@phosphor-icons/react";
import { apiRequest, RenzaiApiError } from "@/shared/api/client";
import { ProviderManager } from "./provider-manager";

type Application = {
  application_id: string;
  name: string;
  status: "active" | "archived";
  privacy_mode: "FULL" | "REDACTED" | "METADATA_ONLY";
  safe_content_persistence: boolean;
  security_retention_days: number;
};
type Environment = {
  environment_id: string;
  type: "development" | "staging" | "production";
  status: "active" | "disabled";
};
type KeyMetadata = {
  key_id: string;
  label: string;
  prefix: string;
  revoked_at: string | null;
  expires_at: string | null;
  last_used_at: string | null;
};
type Finding = {
  finding_id: string;
  detector_id: string;
  category: string;
  severity: string;
  confidence: number;
  safe_explanation: string;
  evidence: { kind: string; text?: string; label?: string; start?: number; end?: number };
};
type Analysis = {
  analysis_id: string;
  safe: boolean;
  action: "allow" | "flag" | "block" | "redact" | "require_review";
  risk_score: number;
  severity: "low" | "medium" | "high" | "critical";
  confidence: number;
  risk_profile: { id: string; name: string; version: number; formula_version: string };
  normalization_version: string;
  detector_ruleset_version: string;
  findings: Finding[];
  risk_contributions: Array<{
    finding_id: string;
    category: string;
    raw_contribution: number;
    status: "retained" | "suppressed";
    corroboration_bonus: number;
    critical_floor_applied: boolean;
  }>;
  risk_explanation: { base_score: number; corroboration_bonus: number; critical_floor: number };
  policy_decision: {
    policy_match: {
      policy_id: string;
      policy_version_id: string;
      version: number;
      scope_kind: string;
    } | null;
    rationale_code: string;
    scope_winners: Array<{ scope_kind: string; action: string; priority: number }>;
  };
  redacted_content?: string;
  timing: {
    normalization_ms: number;
    detector_ms: number;
    risk_ms: number;
    policy_ms: number;
    total_ms: number;
  };
};
type PolicyAction = "allow" | "flag" | "block" | "redact" | "require_review";
type PolicyCondition = { field: string; operator: string; value: string | number | string[] };
type Policy = {
  policy_id: string;
  name: string;
  scope_kind: "organization" | "application" | "environment";
  scope_id: string;
  phase: "input" | "output";
  priority: number;
  enabled: boolean;
  status: "active" | "archived";
  is_baseline: boolean;
  active_version: number;
  latest_version: number;
  version: {
    version: number;
    action: PolicyAction;
    rationale_code: string;
    condition_mode: "all" | "any";
    conditions: PolicyCondition[];
    redaction_targets: string[];
  };
};

const json = (body: object, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function message(error: unknown): string {
  if (error instanceof RenzaiApiError) return `${error.message} (${error.requestId})`;
  return error instanceof Error ? error.message : "Something went wrong.";
}

export function SecurityConsole({
  organizationId,
  role,
  csrfToken,
  view = "all",
}: {
  organizationId: string;
  role: string;
  csrfToken: string;
  view?: "all" | "playground" | "applications" | "providers" | "policies";
}) {
  const queryClient = useQueryClient();
  const canEdit = ["owner", "admin", "developer"].includes(role);
  const canPlay = ["owner", "admin", "security_analyst", "developer"].includes(role);
  const [applicationId, setApplicationId] = useState("");
  const [environmentId, setEnvironmentId] = useState("");
  const [secretOnce, setSecretOnce] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState("");

  const applications = useQuery({
    queryKey: ["applications", organizationId],
    queryFn: () =>
      apiRequest<{ items: Application[] }>(`/api/v1/organizations/${organizationId}/applications`),
  });
  const activeApplication =
    applications.data?.items.find((item) => item.application_id === applicationId) ??
    applications.data?.items[0];
  const environments = useQuery({
    queryKey: ["environments", organizationId, activeApplication?.application_id],
    queryFn: () =>
      apiRequest<{ items: Environment[] }>(
        `/api/v1/organizations/${organizationId}/applications/${activeApplication?.application_id}/environments`,
      ),
    enabled: Boolean(activeApplication),
  });
  const activeEnvironment =
    environments.data?.items.find((item) => item.environment_id === environmentId) ??
    environments.data?.items[0];
  const keys = useQuery({
    queryKey: [
      "keys",
      organizationId,
      activeApplication?.application_id,
      activeEnvironment?.environment_id,
    ],
    queryFn: () =>
      apiRequest<{ items: KeyMetadata[] }>(
        `/api/v1/organizations/${organizationId}/applications/${activeApplication?.application_id}/environments/${activeEnvironment?.environment_id}/keys`,
      ),
    enabled: Boolean(canEdit && activeApplication && activeEnvironment),
  });

  const mutation = useMutation({
    mutationFn: ({ path, init }: { path: string; init: RequestInit }) =>
      apiRequest(path, init, csrfToken),
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["applications", organizationId] });
      await queryClient.invalidateQueries({ queryKey: ["environments", organizationId] });
      await queryClient.invalidateQueries({ queryKey: ["keys", organizationId] });
    },
    onError: (failure) => setError(message(failure)),
  });
  const keyMutation = useMutation({
    mutationFn: async ({ path, body }: { path: string; body: object }) => {
      const response = await apiRequest<{ secret_once: string }>(path, json(body), csrfToken);
      setSecretOnce(response.secret_once);
    },
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["keys", organizationId] });
    },
    onError: (failure) => setError(message(failure)),
    gcTime: 0,
  });
  const analyzeMutation = useMutation({
    mutationFn: (body: object) =>
      apiRequest<Analysis>(
        `/api/v1/organizations/${organizationId}/playground/analyze`,
        json(body),
        csrfToken,
      ),
    onSuccess: (result) => {
      setError("");
      setAnalysis(result);
    },
    onError: (failure) => setError(message(failure)),
  });

  const submit = (
    event: FormEvent<HTMLFormElement>,
    action: (form: FormData) => { path: string; init: RequestInit },
  ) => {
    event.preventDefault();
    mutation.mutate(action(new FormData(event.currentTarget)));
    event.currentTarget.reset();
  };

  const title =
    view === "playground"
      ? "Analysis target"
      : view === "applications"
        ? "Runtime inventory"
        : view === "providers"
          ? "Provider scope"
          : view === "policies"
            ? "Policy scope"
            : "Security controls";

  return (
    <div className={`security-console security-console-${view} page-stack`}>
      <section className="surface-card context-card" aria-labelledby="security-heading">
        <div className="section-heading">
          <div className="icon-tile">
            {view === "playground" ? (
              <FlaskIcon size={22} weight="duotone" />
            ) : view === "applications" ? (
              <AppWindowIcon size={22} weight="duotone" />
            ) : (
              <ShieldCheckIcon size={22} weight="duotone" />
            )}
          </div>
          <div>
            <p className="eyebrow">Tenant-scoped controls</p>
            <h2 id="security-heading">{title}</h2>
            <p>Choose the application and environment for this workspace.</p>
          </div>
        </div>

        <div className="selector-grid">
          <label>
            Application
            <select
              aria-label="Application"
              value={activeApplication?.application_id ?? ""}
              onChange={(event) => {
                setApplicationId(event.target.value);
                setEnvironmentId("");
                setSecretOnce(null);
                setAnalysis(null);
              }}
            >
              {applications.data?.items.map((application) => (
                <option key={application.application_id} value={application.application_id}>
                  {application.name} · {application.status}
                </option>
              ))}
            </select>
          </label>
          <label>
            Environment
            <select
              aria-label="Environment"
              value={activeEnvironment?.environment_id ?? ""}
              onChange={(event) => {
                setEnvironmentId(event.target.value);
                setSecretOnce(null);
                setAnalysis(null);
              }}
              disabled={!activeApplication}
            >
              {environments.data?.items.map((environment) => (
                <option key={environment.environment_id} value={environment.environment_id}>
                  {environment.type} · {environment.status}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {(view === "all" || view === "applications") && canEdit && (
        <section className="surface-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Resource setup</p>
              <h2>Applications and environments</h2>
              <p>Create isolated runtime targets for Renzai analysis and Gateway enforcement.</p>
            </div>
          </div>
          <div className="resource-grid">
            <form
              onSubmit={(event) =>
                submit(event, (form) => ({
                  path: `/api/v1/organizations/${organizationId}/applications`,
                  init: json({ name: form.get("name") }),
                }))
              }
            >
              <div className="form-heading">
                <AppWindowIcon size={20} aria-hidden="true" />
                <h3>Create application</h3>
              </div>
              <input
                name="name"
                aria-label="Application name"
                placeholder="Support copilot"
                required
              />
              <button className="primary">Create application</button>
            </form>
            {activeApplication && (
              <form
                onSubmit={(event) =>
                  submit(event, (form) => ({
                    path: `/api/v1/organizations/${organizationId}/applications/${activeApplication.application_id}/environments`,
                    init: json({ type: form.get("type") }),
                  }))
                }
              >
                <div className="form-heading">
                  <ShieldCheckIcon size={20} aria-hidden="true" />
                  <h3>Create environment</h3>
                </div>
                <select name="type" aria-label="Environment type" defaultValue="development">
                  <option value="development">Development</option>
                  <option value="staging">Staging</option>
                  <option value="production">Production</option>
                </select>
                <button className="primary">Create environment</button>
              </form>
            )}
          </div>
        </section>
      )}

      {(view === "all" || view === "applications") &&
        canEdit &&
        activeApplication &&
        activeEnvironment && (
          <section className="surface-card" aria-labelledby="keys-heading">
            <div className="section-heading">
              <div className="icon-tile">
                <KeyIcon size={21} weight="duotone" />
              </div>
              <div>
                <p className="eyebrow">Write-only credentials</p>
                <h2 id="keys-heading">Environment keys</h2>
                <p>Keys are shown once. Store them in your own secret manager immediately.</p>
              </div>
            </div>
            <form
              className="inline-form"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                keyMutation.mutate({
                  path: `/api/v1/organizations/${organizationId}/applications/${activeApplication.application_id}/environments/${activeEnvironment.environment_id}/keys`,
                  body: { label: form.get("label") },
                });
                event.currentTarget.reset();
              }}
            >
              <input name="label" aria-label="Key label" placeholder="CI integration" required />
              <button className="primary">Create key</button>
            </form>
            {secretOnce && (
              <div className="secret-once" role="status">
                <strong>Copy this key now. It cannot be retrieved again.</strong>
                <code>{secretOnce}</code>
                <button onClick={() => setSecretOnce(null)}>Dismiss secret</button>
              </div>
            )}
            <div className="key-list">
              {keys.data?.items.map((key) => (
                <div key={key.key_id}>
                  <span>
                    <strong>{key.label}</strong> <code>{key.prefix}</code>
                  </span>
                  <span className="actions">
                    <button
                      disabled={Boolean(key.revoked_at)}
                      onClick={() =>
                        keyMutation.mutate({
                          path: `/api/v1/organizations/${organizationId}/applications/${activeApplication.application_id}/environments/${activeEnvironment.environment_id}/keys/${key.key_id}/rotate`,
                          body: {},
                        })
                      }
                    >
                      Rotate
                    </button>
                    <button
                      disabled={Boolean(key.revoked_at)}
                      onClick={() =>
                        mutation.mutate({
                          path: `/api/v1/organizations/${organizationId}/applications/${activeApplication.application_id}/environments/${activeEnvironment.environment_id}/keys/${key.key_id}/revoke`,
                          init: { method: "POST" },
                        })
                      }
                    >
                      Revoke
                    </button>
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

      {(view === "all" || view === "playground") &&
        canPlay &&
        activeApplication &&
        activeEnvironment && (
          <section
            className="surface-card playground-workbench"
            aria-labelledby="playground-heading"
          >
            <div className="section-heading">
              <div>
                <p className="eyebrow">Live inspection</p>
                <h2 id="playground-heading">Test a security decision</h2>
                <p>
                  Content is evaluated by the configured deterministic analysis and policy pipeline.
                </p>
              </div>
            </div>
            <div className="playground-layout">
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  const form = new FormData(event.currentTarget);
                  analyzeMutation.mutate({
                    application_id: activeApplication.application_id,
                    environment_id: activeEnvironment.environment_id,
                    direction: form.get("direction"),
                    content: form.get("content"),
                  });
                }}
              >
                <label>
                  Direction
                  <select name="direction" defaultValue="input">
                    <option value="input">Input</option>
                    <option value="output">Output</option>
                  </select>
                </label>
                <label>
                  Test content
                  <textarea name="content" rows={6} maxLength={32768} required />
                </label>
                <button className="primary" disabled={analyzeMutation.isPending}>
                  {analyzeMutation.isPending ? "Analyzing…" : "Analyze"}
                </button>
              </form>
              {analysis && (
                <div
                  className={`analysis-result analysis-action-${analysis.action}`}
                  aria-live="polite"
                >
                  <header className="decision-hero">
                    <div>
                      <p className="eyebrow">Security decision</p>
                      <h3>{analysis.action.replace("_", " ")}</h3>
                      <p>
                        {analysis.safe
                          ? "No deterministic threat signal was detected."
                          : `${analysis.findings.length} deterministic finding${analysis.findings.length === 1 ? "" : "s"} contributed to this decision.`}
                      </p>
                    </div>
                    <div className="risk-orb">
                      <span>Risk</span>
                      <strong>{analysis.risk_score}</strong>
                      <small>/ 100</small>
                    </div>
                  </header>
                  <div className="risk-summary">
                    <div>
                      <span>Severity</span>
                      <strong>{analysis.severity}</strong>
                    </div>
                    <div>
                      <span>Confidence</span>
                      <strong>{analysis.confidence}%</strong>
                    </div>
                    <div>
                      <span>Action</span>
                      <strong>{analysis.action.replace("_", " ")}</strong>
                    </div>
                    <div>
                      <span>Latency</span>
                      <strong>{analysis.timing.total_ms} ms</strong>
                    </div>
                  </div>
                  <div className="analysis-section-heading">
                    <h4>Deterministic findings</h4>
                    <span className="badge badge-neutral">{analysis.findings.length} total</span>
                  </div>
                  {analysis.findings.map((finding) => (
                    <article key={finding.finding_id}>
                      <p>
                        <strong>{finding.detector_id}</strong> · {finding.category} ·{" "}
                        {finding.severity} · {finding.confidence}% confidence
                      </p>
                      <p>{finding.safe_explanation}</p>
                      <code>
                        {finding.evidence.text ??
                          finding.evidence.label ??
                          `${finding.evidence.kind} ${finding.evidence.start ?? ""}:${finding.evidence.end ?? ""}`}
                      </code>
                    </article>
                  ))}
                  <details>
                    <summary>Risk and technical details</summary>
                    <p>
                      Base {analysis.risk_explanation.base_score} + corroboration{" "}
                      {analysis.risk_explanation.corroboration_bonus}
                      {analysis.risk_explanation.critical_floor
                        ? ` · critical floor ${analysis.risk_explanation.critical_floor}`
                        : ""}
                    </p>
                    <ul>
                      {analysis.risk_contributions.map((contribution) => (
                        <li key={contribution.finding_id}>
                          {contribution.category}: {contribution.raw_contribution} (
                          {contribution.status})
                        </li>
                      ))}
                    </ul>
                  </details>
                  <p>
                    <strong>Policy decision:</strong>{" "}
                    {analysis.policy_decision.policy_match
                      ? `${analysis.policy_decision.policy_match.scope_kind} v${analysis.policy_decision.policy_match.version}`
                      : "no match"}
                    {` · ${analysis.policy_decision.rationale_code}`}
                  </p>
                  {analysis.redacted_content && (
                    <div className="redacted-output">
                      <strong>Redacted output</strong>
                      <pre>{analysis.redacted_content}</pre>
                    </div>
                  )}
                </div>
              )}
              {!analysis && (
                <div className="playground-preview empty-state">
                  <ShieldCheckIcon size={34} weight="duotone" aria-hidden="true" />
                  <h3>Decision appears here</h3>
                  <p>
                    Run an analysis to inspect risk, findings, policy rationale, and any safe
                    redaction.
                  </p>
                </div>
              )}
            </div>
          </section>
        )}
      {(view === "all" || view === "providers") && activeApplication && activeEnvironment && (
        <ProviderManager
          organizationId={organizationId}
          applicationId={activeApplication.application_id}
          environmentId={activeEnvironment.environment_id}
          role={role}
          csrfToken={csrfToken}
        />
      )}
      {(view === "all" || view === "policies") && activeApplication && activeEnvironment && (
        <PolicyManager
          organizationId={organizationId}
          applicationId={activeApplication.application_id}
          environmentId={activeEnvironment.environment_id}
          canEdit={["owner", "admin", "security_analyst"].includes(role)}
          csrfToken={csrfToken}
        />
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

const fieldOperators: Record<string, string[]> = {
  phase: ["equals", "in"],
  category_set: ["equals", "in", "contains_category"],
  detector_id_set: ["equals", "in"],
  risk_score: ["equals", "in", "greater_or_equal", "less_or_equal"],
  severity: ["equals", "in"],
  confidence_band: ["equals", "in"],
  application_id: ["equals", "in"],
  environment_type: ["equals", "in"],
  source: ["equals", "in"],
};

function PolicyManager({
  organizationId,
  applicationId,
  environmentId,
  canEdit,
  csrfToken,
}: {
  organizationId: string;
  applicationId: string;
  environmentId: string;
  canEdit: boolean;
  csrfToken: string;
}) {
  const queryClient = useQueryClient();
  const path = `/api/v1/organizations/${organizationId}/policies`;
  const policies = useQuery({
    queryKey: ["policies", organizationId],
    queryFn: () => apiRequest<{ items: Policy[] }>(path),
  });
  const [editing, setEditing] = useState<Policy | null>(null);
  const [conditions, setConditions] = useState<PolicyCondition[]>([
    { field: "severity", operator: "equals", value: "high" },
  ]);
  const [policyError, setPolicyError] = useState("");
  const policyMutation = useMutation({
    mutationFn: ({ endpoint, init }: { endpoint: string; init: RequestInit }) =>
      apiRequest(endpoint, init, csrfToken),
    onSuccess: async () => {
      setPolicyError("");
      setEditing(null);
      await queryClient.invalidateQueries({ queryKey: ["policies", organizationId] });
    },
    onError: (failure) => setPolicyError(message(failure)),
  });

  const edit = (policy: Policy) => {
    setEditing(policy);
    setConditions(policy.version.conditions);
  };

  return (
    <section className="surface-card policy-manager" aria-labelledby="policies-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Versioned enforcement</p>
          <h2 id="policies-heading">Risk policies</h2>
          <p>First match wins within each scope. The strongest action wins across scopes.</p>
        </div>
      </div>
      <div className="policy-list">
        {policies.data?.items.map((policy) => (
          <article key={policy.policy_id}>
            <div>
              <strong>{policy.name}</strong>{" "}
              {policy.is_baseline && <span className="badge">Baseline</span>}
              <p>
                {policy.scope_kind} · {policy.phase} · priority {policy.priority} ·{" "}
                {policy.version.action} · v{policy.active_version}
                {policy.latest_version > policy.active_version
                  ? ` (v${policy.latest_version} pending)`
                  : ""}
              </p>
            </div>
            {canEdit && policy.status === "active" && (
              <span className="actions">
                <button onClick={() => edit(policy)}>Edit</button>
                <button
                  onClick={() =>
                    policyMutation.mutate({
                      endpoint: `${path}/${policy.policy_id}/${policy.enabled ? "disable" : "enable"}`,
                      init: json({ expected_version: policy.active_version }),
                    })
                  }
                >
                  {policy.enabled ? "Disable" : "Enable"}
                </button>
                {policy.latest_version > policy.active_version && (
                  <button
                    onClick={() =>
                      policyMutation.mutate({
                        endpoint: `${path}/${policy.policy_id}/activate`,
                        init: json({
                          expected_version: policy.active_version,
                          version: policy.latest_version,
                        }),
                      })
                    }
                  >
                    Activate v{policy.latest_version}
                  </button>
                )}
                {policy.active_version > 1 && (
                  <button
                    onClick={() =>
                      policyMutation.mutate({
                        endpoint: `${path}/${policy.policy_id}/rollback`,
                        init: json({
                          expected_version: policy.active_version,
                          version: policy.active_version - 1,
                        }),
                      })
                    }
                  >
                    Roll back
                  </button>
                )}
              </span>
            )}
          </article>
        ))}
      </div>
      {canEdit && (
        <form
          className="policy-form"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const action = String(form.get("action")) as PolicyAction;
            const scopeKind = String(form.get("scope_kind"));
            const body = {
              ...(editing ? { expected_version: editing.active_version } : {}),
              name: form.get("name"),
              ...(!editing
                ? {
                    scope_kind: scopeKind,
                    scope_id:
                      scopeKind === "organization"
                        ? organizationId
                        : scopeKind === "application"
                          ? applicationId
                          : environmentId,
                    phase: form.get("phase"),
                    enabled: true,
                  }
                : {}),
              priority: Number(form.get("priority")),
              action,
              rationale_code: form.get("rationale_code"),
              condition_mode: form.get("condition_mode"),
              conditions: conditions.map((condition) => ({
                ...condition,
                value:
                  condition.field === "risk_score"
                    ? Number(condition.value)
                    : ["in", "equals"].includes(condition.operator) &&
                        ["category_set", "detector_id_set"].includes(condition.field)
                      ? String(condition.value)
                          .split(",")
                          .map((item) => item.trim())
                          .filter(Boolean)
                      : condition.value,
              })),
              redaction_targets:
                action === "redact"
                  ? String(form.get("redaction_targets"))
                      .split(",")
                      .map((item) => item.trim())
                      .filter(Boolean)
                  : [],
            };
            policyMutation.mutate({
              endpoint: editing ? `${path}/${editing.policy_id}` : path,
              init: json(body, editing ? "PATCH" : "POST"),
            });
          }}
        >
          <h4>{editing ? `Create v${editing.latest_version + 1}` : "Create policy"}</h4>
          <div className="selector-grid">
            <label>
              Name
              <input name="name" defaultValue={editing?.name ?? ""} required />
            </label>
            {!editing && (
              <label>
                Scope
                <select name="scope_kind" defaultValue="application">
                  <option value="organization">Organization</option>
                  <option value="application">Application</option>
                  <option value="environment">Environment</option>
                </select>
              </label>
            )}
            {!editing && (
              <label>
                Phase
                <select name="phase" defaultValue="input">
                  <option value="input">Input</option>
                  <option value="output">Output</option>
                </select>
              </label>
            )}
            <label>
              Priority
              <input
                name="priority"
                type="number"
                min="1"
                defaultValue={editing?.priority ?? 500}
                required
              />
            </label>
            <label>
              Action
              <select name="action" defaultValue={editing?.version.action ?? "flag"}>
                <option value="allow">Allow</option>
                <option value="flag">Flag</option>
                <option value="block">Block</option>
                <option value="redact">Redact</option>
                <option value="require_review">Require review</option>
              </select>
            </label>
            <label>
              Rationale code
              <input
                name="rationale_code"
                pattern="[a-z][a-z0-9_]*"
                defaultValue={editing?.version.rationale_code ?? "custom_policy_match"}
                required
              />
            </label>
            <label>
              Match
              <select name="condition_mode" defaultValue={editing?.version.condition_mode ?? "all"}>
                <option value="all">All conditions</option>
                <option value="any">Any condition</option>
              </select>
            </label>
            <label>
              Redaction targets (comma separated)
              <input
                name="redaction_targets"
                defaultValue={editing?.version.redaction_targets.join(", ") ?? ""}
                placeholder="secret_exposure"
              />
            </label>
          </div>
          <fieldset>
            <legend>Conditions</legend>
            {conditions.map((condition, index) => (
              <div className="condition-row" key={`${index}-${condition.field}`}>
                <select
                  aria-label={`Condition ${index + 1} field`}
                  value={condition.field}
                  onChange={(event) => {
                    const next = [...conditions];
                    const field = event.target.value;
                    next[index] = { field, operator: fieldOperators[field][0], value: "" };
                    setConditions(next);
                  }}
                >
                  {Object.keys(fieldOperators).map((field) => (
                    <option key={field} value={field}>
                      {field}
                    </option>
                  ))}
                </select>
                <select
                  aria-label={`Condition ${index + 1} operator`}
                  value={condition.operator}
                  onChange={(event) => {
                    const next = [...conditions];
                    next[index] = { ...condition, operator: event.target.value };
                    setConditions(next);
                  }}
                >
                  {fieldOperators[condition.field].map((operator) => (
                    <option key={operator} value={operator}>
                      {operator}
                    </option>
                  ))}
                </select>
                <input
                  aria-label={`Condition ${index + 1} value`}
                  value={String(condition.value)}
                  onChange={(event) => {
                    const next = [...conditions];
                    next[index] = { ...condition, value: event.target.value };
                    setConditions(next);
                  }}
                  required
                />
                <button
                  type="button"
                  disabled={conditions.length === 1}
                  onClick={() => setConditions(conditions.filter((_, row) => row !== index))}
                >
                  Remove
                </button>
              </div>
            ))}
            <button
              type="button"
              disabled={conditions.length >= 20}
              onClick={() =>
                setConditions([
                  ...conditions,
                  { field: "severity", operator: "equals", value: "high" },
                ])
              }
            >
              Add condition
            </button>
          </fieldset>
          <span className="actions">
            <button className="primary" disabled={policyMutation.isPending}>
              {editing ? "Save new version" : "Create policy"}
            </button>
            {editing && (
              <button type="button" onClick={() => setEditing(null)}>
                Cancel
              </button>
            )}
          </span>
        </form>
      )}
      {policyError && (
        <p className="error" role="alert">
          {policyError}
        </p>
      )}
    </section>
  );
}
