import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryProvider } from "@/shared/context/query-provider";
import { AIIntelligencePanel } from "./ai-intelligence-panel";

describe("AI intelligence incident panel", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("labels advisory content, shows provenance, and requests bounded task types", async () => {
    const requests: Array<{ path: string; body: string }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const path = String(input);
      requests.push({ path, body: String(init?.body ?? "") });
      if (path.endsWith("/ai-providers"))
        return response({ items: [{ config_id: "ai-1", status: "active" }] });
      if (init?.method === "POST")
        return response({
          request_id: "request-2",
          task_type: "incident_summary",
          status: "pending",
        });
      return response({
        items: [
          {
            request_id: "request-1",
            task_type: "attack_explanation",
            status: "completed",
            ai_generated: true,
            context_mode: "redacted",
            incident_version: 3,
            provider_name: "Dedicated helper",
            model: "safe-model",
            prompt_template_version: "attack-explanation-v1",
            content: {
              interpretation: "Possible instruction override.",
              observed_techniques: ["role manipulation"],
              uncertainty: "Advisory interpretation only.",
            },
            error_code: null,
            created_at: "2026-10-02T00:00:00Z",
            completed_at: "2026-10-02T00:00:01Z",
          },
          {
            request_id: "request-mitigation",
            task_type: "mitigation_suggestion",
            status: "completed",
            ai_generated: true,
            context_mode: "redacted",
            incident_version: 3,
            provider_name: "Dedicated helper",
            model: "safe-model",
            prompt_template_version: "mitigation-v1",
            content: {
              recommendations: [
                {
                  title: "Review input boundaries",
                  rationale: "Reduce untrusted instruction influence.",
                  priority: "high",
                },
              ],
            },
            error_code: null,
            created_at: "2026-10-02T00:00:00Z",
            completed_at: "2026-10-02T00:00:01Z",
          },
          {
            request_id: "request-policy",
            task_type: "policy_suggestion",
            status: "completed",
            ai_generated: true,
            context_mode: "redacted",
            incident_version: 3,
            provider_name: "Dedicated helper",
            model: "safe-model",
            prompt_template_version: "policy-suggestion-v1",
            content: {
              rationale: "Operator review required.",
              proposed_policy: {
                action: "require_review",
                scope_kind: "organization",
                phase: "input",
                priority: 50,
                conditions: [{ field: "risk_score", operator: "greater_or_equal", value: 70 }],
              },
            },
            error_code: null,
            created_at: "2026-10-02T00:00:00Z",
            completed_at: "2026-10-02T00:00:01Z",
          },
        ],
      });
    });

    render(
      <QueryProvider>
        <AIIntelligencePanel
          organizationId="org-1"
          incidentId="incident-1"
          role="security_analyst"
          csrfToken="csrf"
        />
      </QueryProvider>,
    );

    expect(await screen.findByText("Possible instruction override.")).toBeVisible();
    expect(screen.getByText(/Advisory, AI-generated assistance/)).toBeVisible();
    expect(screen.getByText(/attack-explanation-v1/)).toBeVisible();
    expect(screen.getAllByText(/context redacted · incident v3/)).toHaveLength(3);
    expect(screen.getByText("Review input boundaries").closest("li")).toHaveTextContent(
      "Reduce untrusted instruction influence.",
    );
    expect(screen.getByText("risk_score greater_or_equal 70")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Generate summary" }));
    await waitFor(() =>
      expect(
        requests.some(
          ({ body }) =>
            body.includes('"task_type":"incident_summary"') &&
            body.includes('"disclosure_mode":"redacted"'),
        ),
      ).toBe(true),
    );
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("keeps viewers read-only and treats absent configuration as optional", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input).endsWith("/ai-providers")) return response({ items: [] });
      return response({ items: [] });
    });
    render(
      <QueryProvider>
        <AIIntelligencePanel
          organizationId="org-1"
          incidentId="incident-1"
          role="viewer"
          csrfToken="csrf"
        />
      </QueryProvider>,
    );
    expect(
      await screen.findByText("AI intelligence is optional and is not configured."),
    ).toBeVisible();
    expect(screen.queryByRole("button", { name: "Generate summary" })).not.toBeInTheDocument();
  });
});

function response(body: object): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
