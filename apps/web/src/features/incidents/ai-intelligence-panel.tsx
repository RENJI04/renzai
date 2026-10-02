"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, RenzaiApiError } from "@/shared/api/client";

type TaskType =
  "incident_summary" | "attack_explanation" | "mitigation_suggestion" | "policy_suggestion";
type AIResult = {
  request_id: string;
  task_type: TaskType;
  status: "pending" | "running" | "completed" | "failed";
  ai_generated: true;
  context_mode: "metadata_only" | "redacted" | "full";
  incident_version: number;
  provider_name: string;
  model: string;
  prompt_template_version: string | null;
  content: Record<string, unknown> | null;
  error_code: string | null;
  created_at: string;
  completed_at: string | null;
};
type AIProvider = { config_id: string; status: "active" | "disabled" };

const taskLabels: Record<TaskType, string> = {
  incident_summary: "Generate summary",
  attack_explanation: "Explain attack",
  mitigation_suggestion: "Suggest mitigations",
  policy_suggestion: "Suggest policy",
};

function readable(value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map(readable).join(" · ");
  return "";
}

function recordValue(value: unknown): Record<string, unknown> | undefined {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return undefined;
  return value as Record<string, unknown>;
}

export function AIIntelligencePanel({
  organizationId,
  incidentId,
  role,
  csrfToken,
}: {
  organizationId: string;
  incidentId: string;
  role: string;
  csrfToken: string;
}) {
  const queryClient = useQueryClient();
  const canRequest = ["owner", "admin", "security_analyst"].includes(role);
  const providers = useQuery({
    queryKey: ["ai-providers", organizationId],
    queryFn: () =>
      apiRequest<{ items: AIProvider[] }>(`/api/v1/organizations/${organizationId}/ai-providers`),
  });
  const results = useQuery({
    queryKey: ["ai-intelligence", organizationId, incidentId],
    queryFn: () =>
      apiRequest<{ items: AIResult[] }>(
        `/api/v1/organizations/${organizationId}/incidents/${incidentId}/ai-analysis`,
      ),
    refetchInterval: (query) =>
      query.state.data?.items.some((item) => ["pending", "running"].includes(item.status))
        ? 3000
        : false,
  });
  const request = useMutation({
    mutationFn: (taskType: TaskType) =>
      apiRequest<AIResult>(
        `/api/v1/organizations/${organizationId}/incidents/${incidentId}/ai-analysis`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Renzai-CSRF": csrfToken,
            "Idempotency-Key": `${incidentId}-${taskType}-${crypto.randomUUID()}`,
          },
          body: JSON.stringify({ task_type: taskType, disclosure_mode: "redacted" }),
        },
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["ai-intelligence", organizationId, incidentId],
      }),
  });
  const configured = providers.data?.items.some((item) => item.status === "active") ?? false;
  const inFlight = new Set(
    results.data?.items
      .filter((item) => ["pending", "running"].includes(item.status))
      .map((item) => item.task_type) ?? [],
  );

  return (
    <section className="ai-intelligence" aria-label="AI Intelligence">
      <header>
        <div>
          <h4>AI Intelligence</h4>
          <p className="muted">
            Advisory, AI-generated assistance. It cannot change deterministic findings or policy
            enforcement.
          </p>
        </div>
        <span className="ai-label">AI-generated</span>
      </header>

      {!providers.isLoading && !configured && (
        <p className="muted">AI intelligence is optional and is not configured.</p>
      )}
      {configured && canRequest && (
        <div className="ai-actions">
          {(Object.keys(taskLabels) as TaskType[]).map((taskType) => (
            <button
              key={taskType}
              disabled={request.isPending || inFlight.has(taskType)}
              onClick={() => request.mutate(taskType)}
            >
              {inFlight.has(taskType) ? "In progress…" : taskLabels[taskType]}
            </button>
          ))}
        </div>
      )}
      {request.error && (
        <p className="error" role="alert">
          {request.error instanceof RenzaiApiError
            ? `${request.error.message} (${request.error.requestId})`
            : "AI request failed."}
        </p>
      )}

      <div className="ai-results">
        {results.data?.items.map((item) => (
          <article key={item.request_id}>
            <header>
              <strong>{taskLabels[item.task_type]}</strong>
              <span>{item.status}</span>
            </header>
            {item.status === "completed" && item.content && (
              <AIContent taskType={item.task_type} content={item.content} />
            )}
            {item.status === "failed" && (
              <p className="muted">AI assistance failed safely ({item.error_code}).</p>
            )}
            <small>
              {item.provider_name} · {item.model} · {item.prompt_template_version ?? "queued"} ·
              context {item.context_mode} · incident v{item.incident_version} ·
              {new Date(item.completed_at ?? item.created_at).toLocaleString()}
            </small>
          </article>
        ))}
      </div>
    </section>
  );
}

function AIContent({
  taskType,
  content,
}: {
  taskType: TaskType;
  content: Record<string, unknown>;
}) {
  if (taskType === "incident_summary") {
    return (
      <div>
        <p>{readable(content.summary)}</p>
        <p>{readable(content.key_points)}</p>
      </div>
    );
  }
  if (taskType === "attack_explanation") {
    return (
      <div>
        <p>
          <strong>Possible interpretation:</strong> {readable(content.interpretation)}
        </p>
        <p>{readable(content.observed_techniques)}</p>
        <p className="muted">Uncertainty: {readable(content.uncertainty)}</p>
      </div>
    );
  }
  if (taskType === "mitigation_suggestion") {
    const recommendations = Array.isArray(content.recommendations)
      ? content.recommendations.map(recordValue).filter((item) => item !== undefined)
      : [];
    return (
      <ul>
        {recommendations.map((recommendation, index) => (
          <li key={`${readable(recommendation.title)}-${index}`}>
            <strong>{readable(recommendation.title)}</strong> ({readable(recommendation.priority)})
            <br />
            {readable(recommendation.rationale)}
          </li>
        ))}
      </ul>
    );
  }
  const proposal = recordValue(content.proposed_policy);
  const conditions = Array.isArray(proposal?.conditions)
    ? proposal.conditions.map(recordValue).filter((item) => item !== undefined)
    : [];
  return (
    <div>
      <p>{readable(content.rationale)}</p>
      {proposal && (
        <dl className="incident-facts">
          <div>
            <dt>Draft action</dt>
            <dd>{readable(proposal.action)}</dd>
          </div>
          <div>
            <dt>Scope</dt>
            <dd>{readable(proposal.scope_kind)}</dd>
          </div>
          <div>
            <dt>Phase</dt>
            <dd>{readable(proposal.phase)}</dd>
          </div>
          <div>
            <dt>Priority</dt>
            <dd>{readable(proposal.priority)}</dd>
          </div>
          <div>
            <dt>Conditions</dt>
            <dd>
              {conditions.map((condition, index) => (
                <span key={`${readable(condition.field)}-${index}`}>
                  {index > 0 ? "; " : ""}
                  {readable(condition.field)} {readable(condition.operator)}{" "}
                  {readable(condition.value)}
                </span>
              ))}
            </dd>
          </div>
        </dl>
      )}
      <p className="muted">Validated draft only. Review it in the normal policy workflow.</p>
    </div>
  );
}
