"use client";

import { FormEvent, useMemo, useState } from "react";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, RenzaiApiError } from "@/shared/api/client";
import { AIIntelligencePanel } from "./ai-intelligence-panel";

type Status = "open" | "investigating" | "resolved" | "ignored" | "false_positive";
type Severity = "low" | "medium" | "high" | "critical";
type IncidentSummary = {
  incident_id: string;
  title: string;
  safe_summary: string;
  status: Status;
  severity: Severity;
  risk_score: number | null;
  application_name: string | null;
  environment_name: string | null;
  source: string;
  action: string | null;
  category: string | null;
  assignee_user_id: string | null;
  assignee_email: string | null;
  version: number;
  created_at: string;
};
type TimelineItem = {
  timeline_event_id: string;
  event_type: string;
  actor_email: string | null;
  safe_summary: string;
  created_at: string;
};
type Comment = {
  comment_id: string;
  author_email: string;
  body: string;
  created_at: string;
};
type Analysis = {
  state: "available" | "content_no_longer_retained";
  analysis_id?: string;
  event_id?: string;
  privacy_mode?: string;
  content?: string;
  content_state?: string;
  risk_explanation?: {
    base_score: number;
    corroboration_bonus: number;
    critical_floor: number;
    profile_version: number;
  };
  findings?: Array<{
    finding_id: string;
    category: string;
    detector_id: string;
    severity: string;
    confidence: number;
    safe_explanation: string;
  }>;
  policy_decision?: { action: string; rationale_code: string } | null;
};
type IncidentDetail = IncidentSummary & {
  analysis: Analysis | null;
  timeline: TimelineItem[];
  comments: Comment[];
  related_analyses: Array<{ event_id: string; analysis_id: string; reason: string }>;
};
type Assignee = { user_id: string; email: string; role: string };
type Application = { application_id: string; name: string };
type Environment = { environment_id: string; type: string };

const transitions: Record<Status, Status[]> = {
  open: ["investigating", "resolved", "ignored", "false_positive"],
  investigating: ["open", "resolved", "ignored", "false_positive"],
  resolved: ["investigating"],
  ignored: ["investigating"],
  false_positive: ["investigating"],
};

const json = (body: object, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function errorMessage(error: unknown): string {
  if (error instanceof RenzaiApiError) return `${error.message} (${error.requestId})`;
  return error instanceof Error ? error.message : "Incident operation failed.";
}

export function IncidentConsole({
  organizationId,
  role,
  csrfToken,
}: {
  organizationId: string;
  role: string;
  csrfToken: string;
}) {
  const queryClient = useQueryClient();
  const canEdit = ["owner", "admin", "security_analyst"].includes(role);
  const canComment = canEdit || role === "developer";
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [applicationId, setApplicationId] = useState("");
  const [environmentId, setEnvironmentId] = useState("");
  const [assigneeId, setAssigneeId] = useState("");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [error, setError] = useState("");
  const query = new URLSearchParams();
  if (status) query.set("status", status);
  if (severity) query.set("severity", severity);
  if (applicationId) query.set("application_id", applicationId);
  if (environmentId) query.set("environment_id", environmentId);
  if (assigneeId === "unassigned") query.set("unassigned", "true");
  else if (assigneeId) query.set("assignee_user_id", assigneeId);
  if (search.trim()) query.set("search", search.trim());

  const applications = useQuery({
    queryKey: ["applications", organizationId],
    queryFn: () =>
      apiRequest<{ items: Application[] }>(`/api/v1/organizations/${organizationId}/applications`),
  });
  const environments = useQuery({
    queryKey: ["environments", organizationId, applicationId],
    queryFn: () =>
      apiRequest<{ items: Environment[] }>(
        `/api/v1/organizations/${organizationId}/applications/${applicationId}/environments`,
      ),
    enabled: Boolean(applicationId),
  });
  const queue = useInfiniteQuery({
    queryKey: [
      "incidents",
      organizationId,
      status,
      severity,
      applicationId,
      environmentId,
      assigneeId,
      search,
    ],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) => {
      const pageQuery = new URLSearchParams(query);
      if (pageParam) pageQuery.set("cursor", pageParam);
      return apiRequest<{ items: IncidentSummary[]; next_cursor: string | null }>(
        `/api/v1/organizations/${organizationId}/incidents?${pageQuery.toString()}`,
      );
    },
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
  const queueItems = queue.data?.pages.flatMap((page) => page.items) ?? [];
  const activeIncidentId = queueItems.some((item) => item.incident_id === selectedId)
    ? selectedId
    : (queueItems[0]?.incident_id ?? "");

  const detail = useQuery({
    queryKey: ["incident", organizationId, activeIncidentId],
    queryFn: () =>
      apiRequest<IncidentDetail>(
        `/api/v1/organizations/${organizationId}/incidents/${activeIncidentId}`,
      ),
    enabled: Boolean(activeIncidentId),
  });
  const assignees = useQuery({
    queryKey: ["incident-assignees", organizationId],
    queryFn: () =>
      apiRequest<{ items: Assignee[] }>(
        `/api/v1/organizations/${organizationId}/incidents/assignees`,
      ),
    enabled: canEdit,
  });
  const validTransitions = useMemo(
    () => (detail.data ? transitions[detail.data.status] : []),
    [detail.data],
  );

  const mutate = useMutation({
    mutationFn: ({ path, init }: { path: string; init: RequestInit }) =>
      apiRequest<unknown>(path, init, csrfToken),
    onSuccess: async () => {
      setError("");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["incidents", organizationId] }),
        queryClient.invalidateQueries({
          queryKey: ["incident", organizationId, activeIncidentId],
        }),
      ]);
    },
    onError: (failure) => setError(errorMessage(failure)),
  });

  const updateStatus = (next: Status) => {
    if (!detail.data) return;
    const reopening = ["resolved", "ignored", "false_positive"].includes(detail.data.status);
    const reason = reopening ? window.prompt("Reason for reopening this incident") : null;
    if (reopening && !reason) return;
    mutate.mutate({
      path: `/api/v1/organizations/${organizationId}/incidents/${detail.data.incident_id}/status`,
      init: json({ status: next, version: detail.data.version, reason }, "PATCH"),
    });
  };

  const submitComment = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!detail.data) return;
    const form = new FormData(event.currentTarget);
    mutate.mutate({
      path: `/api/v1/organizations/${organizationId}/incidents/${detail.data.incident_id}/comments`,
      init: json({ body: form.get("body") }),
    });
    event.currentTarget.reset();
  };

  return (
    <section className="panel incident-console" aria-labelledby="incident-heading">
      <p className="eyebrow">INCIDENT MANAGEMENT</p>
      <h2 id="incident-heading">Incident Queue</h2>
      <p className="phase-note">
        Durable, tenant-scoped investigations linked to the original security decision.
      </p>
      <div className="incident-filters" aria-label="Incident filters">
        <label>
          Status
          <select
            aria-label="Incident status filter"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="">All statuses</option>
            {Object.keys(transitions).map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Severity
          <select
            aria-label="Incident severity filter"
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
          >
            <option value="">All severities</option>
            {(["critical", "high", "medium", "low"] as Severity[]).map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Application
          <select
            aria-label="Incident application filter"
            value={applicationId}
            onChange={(event) => {
              setApplicationId(event.target.value);
              setEnvironmentId("");
            }}
          >
            <option value="">All applications</option>
            {applications.data?.items.map((application) => (
              <option key={application.application_id} value={application.application_id}>
                {application.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Environment
          <select
            aria-label="Incident environment filter"
            value={environmentId}
            disabled={!applicationId}
            onChange={(event) => setEnvironmentId(event.target.value)}
          >
            <option value="">All environments</option>
            {environments.data?.items.map((environment) => (
              <option key={environment.environment_id} value={environment.environment_id}>
                {environment.type}
              </option>
            ))}
          </select>
        </label>
        <label>
          Assignee
          <select
            aria-label="Incident assignee filter"
            value={assigneeId}
            onChange={(event) => setAssigneeId(event.target.value)}
          >
            <option value="">All assignees</option>
            <option value="unassigned">Unassigned</option>
            {assignees.data?.items.map((assignee) => (
              <option key={assignee.user_id} value={assignee.user_id}>
                {assignee.email}
              </option>
            ))}
          </select>
        </label>
        <label>
          Search safe metadata
          <input
            aria-label="Incident search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            maxLength={120}
          />
        </label>
      </div>

      <div className="incident-layout">
        <div className="incident-list" aria-label="Incident queue results">
          {queue.isLoading && <p className="muted">Loading incidents…</p>}
          {queueItems.map((incident) => (
            <button
              className={incident.incident_id === activeIncidentId ? "active" : ""}
              key={incident.incident_id}
              onClick={() => setSelectedId(incident.incident_id)}
            >
              <span className={`severity severity-${incident.severity}`}>{incident.severity}</span>
              <strong>{incident.title}</strong>
              <small>
                {incident.application_name ?? "Organization"} ·{" "}
                {incident.environment_name ?? "Any environment"}
              </small>
              <small>
                {incident.status} · risk {incident.risk_score ?? "—"} ·{" "}
                {incident.action ?? incident.source}
              </small>
              <small>
                {incident.category ?? "security event"} · {incident.assignee_email ?? "Unassigned"}
              </small>
              <small>{new Date(incident.created_at).toLocaleString()}</small>
            </button>
          ))}
          {queue.data && queueItems.length === 0 && (
            <p className="muted">No incidents match these filters.</p>
          )}
          {queue.hasNextPage && (
            <button onClick={() => void queue.fetchNextPage()} disabled={queue.isFetchingNextPage}>
              {queue.isFetchingNextPage ? "Loading…" : "Load more incidents"}
            </button>
          )}
        </div>

        {detail.data && (
          <article className="incident-detail" aria-label="Incident detail">
            <header>
              <div>
                <span className={`severity severity-${detail.data.severity}`}>
                  {detail.data.severity}
                </span>
                <h3>{detail.data.title}</h3>
                <p>{detail.data.safe_summary}</p>
              </div>
              <strong>{detail.data.status}</strong>
            </header>
            <dl className="incident-facts">
              <div>
                <dt>Risk</dt>
                <dd>{detail.data.risk_score ?? "—"}</dd>
              </div>
              <div>
                <dt>Source</dt>
                <dd>{detail.data.source}</dd>
              </div>
              <div>
                <dt>Action</dt>
                <dd>{detail.data.action ?? "—"}</dd>
              </div>
              <div>
                <dt>Threat</dt>
                <dd>{detail.data.category ?? "security event"}</dd>
              </div>
              <div>
                <dt>Application</dt>
                <dd>{detail.data.application_name ?? "Organization"}</dd>
              </div>
              <div>
                <dt>Environment</dt>
                <dd>{detail.data.environment_name ?? "Any environment"}</dd>
              </div>
              <div>
                <dt>Assignee</dt>
                <dd>{detail.data.assignee_email ?? "Unassigned"}</dd>
              </div>
            </dl>

            {canEdit && (
              <div className="incident-actions">
                <label>
                  Status
                  <select
                    aria-label="Update incident status"
                    value=""
                    onChange={(event) => updateStatus(event.target.value as Status)}
                  >
                    <option value="">Choose transition</option>
                    {validTransitions.map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Assignee
                  <select
                    aria-label="Incident assignee"
                    value={detail.data.assignee_user_id ?? ""}
                    onChange={(event) =>
                      mutate.mutate({
                        path: `/api/v1/organizations/${organizationId}/incidents/${detail.data.incident_id}/assignment`,
                        init: json(
                          {
                            assignee_user_id: event.target.value || null,
                            version: detail.data.version,
                          },
                          "PATCH",
                        ),
                      })
                    }
                  >
                    <option value="">Unassigned</option>
                    {assignees.data?.items.map((assignee) => (
                      <option key={assignee.user_id} value={assignee.user_id}>
                        {assignee.email} · {assignee.role}
                      </option>
                    ))}
                  </select>
                </label>
                {validTransitions.includes("false_positive") && (
                  <button onClick={() => updateStatus("false_positive")}>
                    Mark as false positive
                  </button>
                )}
              </div>
            )}
            <p className="false-positive-note">
              False-positive classification does not modify detectors, risk weights, or policies.
            </p>

            <section>
              <h4>Deterministic Security Evidence</h4>
              {detail.data.analysis?.state === "content_no_longer_retained" ? (
                <p className="muted">
                  Content no longer retained. Incident metadata remains available.
                </p>
              ) : detail.data.analysis ? (
                <>
                  <p>
                    Analysis {detail.data.analysis.analysis_id} · Event{" "}
                    {detail.data.analysis.event_id}
                  </p>
                  {detail.data.analysis.content ? (
                    <pre>{detail.data.analysis.content}</pre>
                  ) : (
                    <p className="muted">
                      Content not retained under {detail.data.analysis.privacy_mode} privacy mode.
                    </p>
                  )}
                  <div className="finding-list">
                    {detail.data.analysis.findings?.map((finding) => (
                      <div key={finding.finding_id}>
                        <strong>{finding.category}</strong>
                        <span>
                          {finding.safe_explanation} · confidence {finding.confidence}
                        </span>
                      </div>
                    ))}
                  </div>
                  <p>
                    Policy: {detail.data.analysis.policy_decision?.action ?? "none"} ·{" "}
                    {detail.data.analysis.policy_decision?.rationale_code ?? "no match"}
                  </p>
                  {detail.data.analysis.risk_explanation && (
                    <p>
                      Risk explanation: base {detail.data.analysis.risk_explanation.base_score},
                      corroboration +{detail.data.analysis.risk_explanation.corroboration_bonus},
                      critical floor {detail.data.analysis.risk_explanation.critical_floor}, profile
                      v{detail.data.analysis.risk_explanation.profile_version}.
                    </p>
                  )}
                </>
              ) : (
                <p>Manual incident; no linked analysis.</p>
              )}
              {detail.data.related_analyses.length > 0 && (
                <ul>
                  {detail.data.related_analyses.map((related) => (
                    <li key={related.event_id}>
                      Event {related.event_id} · Analysis {related.analysis_id} · {related.reason}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <AIIntelligencePanel
              organizationId={organizationId}
              incidentId={detail.data.incident_id}
              role={role}
              csrfToken={csrfToken}
            />

            <section>
              <h4>Timeline</h4>
              <ol className="timeline">
                {detail.data.timeline.map((item) => (
                  <li key={item.timeline_event_id}>
                    <strong>{item.safe_summary}</strong>
                    <span>
                      {item.actor_email ?? "Renzai service"} ·{" "}
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  </li>
                ))}
              </ol>
            </section>
            <section>
              <h4>Comments</h4>
              <div className="comment-list">
                {detail.data.comments.map((comment) => (
                  <p key={comment.comment_id}>
                    <strong>{comment.author_email}</strong>
                    <span>{comment.body}</span>
                  </p>
                ))}
              </div>
              {canComment && (
                <form className="comment-form" onSubmit={submitComment}>
                  <label>
                    Plain-text comment
                    <textarea name="body" required maxLength={4000} />
                  </label>
                  <button className="primary" disabled={mutate.isPending}>
                    Add comment
                  </button>
                </form>
              )}
            </section>
          </article>
        )}
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
