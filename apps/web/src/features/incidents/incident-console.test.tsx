import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryProvider } from "@/shared/context/query-provider";
import { IncidentConsole } from "./incident-console";

const summary = {
  incident_id: "incident-1",
  title: "High prompt injection blocked",
  safe_summary: "gateway input block; prompt injection; risk 84/100.",
  status: "open",
  severity: "high",
  risk_score: 84,
  application_name: "Assistant",
  environment_name: "production",
  source: "gateway",
  action: "block",
  category: "prompt_injection",
  assignee_user_id: null,
  assignee_email: null,
  version: 1,
  created_at: "2026-10-01T00:00:00Z",
};

const detail = {
  ...summary,
  related_analyses: [{ event_id: "event-1", analysis_id: "analysis-1", reason: "policy" }],
  analysis: {
    state: "available",
    analysis_id: "analysis-1",
    event_id: "event-1",
    privacy_mode: "REDACTED",
    content_state: "not_retained",
    risk_explanation: {
      base_score: 84,
      corroboration_bonus: 0,
      critical_floor: 0,
      profile_version: 1,
    },
    findings: [
      {
        finding_id: "finding-1",
        category: "prompt_injection",
        detector_id: "prompt-injection-v1",
        severity: "high",
        confidence: 98,
        safe_explanation: "Instruction override pattern detected.",
      },
    ],
    policy_decision: { action: "block", rationale_code: "production_input_block" },
  },
  timeline: [
    {
      timeline_event_id: "timeline-1",
      event_type: "incident_created",
      actor_email: null,
      safe_summary: "Incident created from a Gateway policy action.",
      created_at: "2026-10-01T00:00:00Z",
    },
  ],
  comments: [
    {
      comment_id: "comment-1",
      author_email: "analyst@example.com",
      body: "Investigating safely.",
      created_at: "2026-10-01T00:01:00Z",
    },
  ],
};

describe("incident console", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders the queue/detail and drives filters, lifecycle, assignment, comments, and false positives", async () => {
    const requests: Array<{ path: string; method: string; body: string }> = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const path = String(input);
      const method = init?.method ?? "GET";
      requests.push({ path, method, body: String(init?.body ?? "") });
      if (path.endsWith("/applications"))
        return jsonResponse({ items: [{ application_id: "app-1", name: "Assistant" }] });
      if (path.endsWith("/applications/app-1/environments"))
        return jsonResponse({ items: [{ environment_id: "env-1", type: "production" }] });
      if (path.endsWith("/incidents/assignees"))
        return jsonResponse({
          items: [{ user_id: "user-1", email: "owner@example.com", role: "owner" }],
        });
      if (path.endsWith("/ai-providers")) return jsonResponse({ items: [] });
      if (path.endsWith("/incidents/incident-1/ai-analysis")) return jsonResponse({ items: [] });
      if (path.includes("/incidents/incident-1/") && method !== "GET") return jsonResponse(detail);
      if (path.endsWith("/incidents/incident-1")) return jsonResponse(detail);
      if (path.includes("/incidents?"))
        return jsonResponse({ items: [summary], next_cursor: null });
      throw new Error(`Unexpected request: ${path}`);
    });

    renderConsole("owner");
    expect(await screen.findByText("High prompt injection blocked")).toBeVisible();
    expect(
      await screen.findByText("Instruction override pattern detected. · confidence 98"),
    ).toBeVisible();
    expect(screen.getByText("Investigating safely.")).toBeVisible();
    expect(screen.getByText(/Content not retained under REDACTED/)).toBeVisible();
    expect(screen.getByText(/Risk explanation: base 84/)).toBeVisible();
    expect(screen.getByText(/Event event-1 · Analysis analysis-1/)).toBeVisible();
    expect(screen.getByText("Deterministic Security Evidence")).toBeVisible();
    expect(
      await screen.findByText(/AI intelligence is optional and is not configured/),
    ).toBeVisible();

    fireEvent.change(screen.getByLabelText("Incident status filter"), {
      target: { value: "open" },
    });
    fireEvent.change(screen.getByLabelText("Incident severity filter"), {
      target: { value: "high" },
    });
    fireEvent.change(await screen.findByLabelText("Incident application filter"), {
      target: { value: "app-1" },
    });
    fireEvent.change(await screen.findByLabelText("Incident environment filter"), {
      target: { value: "env-1" },
    });
    fireEvent.change(screen.getByLabelText("Incident assignee filter"), {
      target: { value: "unassigned" },
    });
    fireEvent.change(screen.getByLabelText("Incident search"), { target: { value: "prompt" } });
    await waitFor(() =>
      expect(
        requests.some(
          ({ path }) =>
            path.includes("status=open") &&
            path.includes("severity=high") &&
            path.includes("application_id=app-1") &&
            path.includes("environment_id=env-1") &&
            path.includes("unassigned=true") &&
            path.includes("search=prompt"),
        ),
      ).toBe(true),
    );

    fireEvent.change(await screen.findByLabelText("Update incident status"), {
      target: { value: "investigating" },
    });
    fireEvent.change(screen.getByLabelText("Incident assignee"), { target: { value: "user-1" } });
    fireEvent.change(screen.getByLabelText("Plain-text comment"), {
      target: { value: "Plain text only" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add comment" }));
    fireEvent.click(screen.getByRole("button", { name: "Mark as false positive" }));

    await waitFor(() => {
      expect(
        requests.some(
          ({ path, body }) => path.endsWith("/status") && body.includes("investigating"),
        ),
      ).toBe(true);
      expect(
        requests.some(({ path, body }) => path.endsWith("/assignment") && body.includes("user-1")),
      ).toBe(true);
      expect(
        requests.some(
          ({ path, body }) => path.endsWith("/comments") && body.includes("Plain text only"),
        ),
      ).toBe(true);
      expect(
        requests.some(
          ({ path, body }) => path.endsWith("/status") && body.includes("false_positive"),
        ),
      ).toBe(true);
    });
    expect(screen.getByText(/does not modify detectors, risk weights, or policies/i)).toBeVisible();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("gates operator controls by role and renders expired-content state", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      if (path.endsWith("/applications")) return jsonResponse({ items: [] });
      if (path.endsWith("/ai-providers")) return jsonResponse({ items: [] });
      if (path.endsWith("/incidents/incident-1/ai-analysis")) return jsonResponse({ items: [] });
      if (path.endsWith("/incidents/incident-1"))
        return jsonResponse({ ...detail, analysis: { state: "content_no_longer_retained" } });
      if (path.includes("/incidents?"))
        return jsonResponse({ items: [summary], next_cursor: null });
      throw new Error(`Unexpected request: ${path}`);
    });

    renderConsole("developer");
    expect(await screen.findByText(/Content no longer retained/)).toBeVisible();
    expect(screen.queryByLabelText("Update incident status")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Incident assignee")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Plain-text comment")).toBeVisible();
  });

  it("loads the next cursor page and keeps viewers read-only", async () => {
    const requests: string[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      requests.push(path);
      if (path.endsWith("/applications")) return jsonResponse({ items: [] });
      if (path.endsWith("/ai-providers")) return jsonResponse({ items: [] });
      if (path.endsWith("/incidents/incident-1/ai-analysis")) return jsonResponse({ items: [] });
      if (path.endsWith("/incidents/incident-2/ai-analysis")) return jsonResponse({ items: [] });
      if (path.endsWith("/incidents/incident-1")) return jsonResponse(detail);
      if (path.endsWith("/incidents/incident-2"))
        return jsonResponse({ ...detail, incident_id: "incident-2", title: "Second incident" });
      if (path.includes("cursor=next-page"))
        return jsonResponse({
          items: [{ ...summary, incident_id: "incident-2", title: "Second incident" }],
          next_cursor: null,
        });
      if (path.includes("/incidents?"))
        return jsonResponse({ items: [summary], next_cursor: "next-page" });
      throw new Error(`Unexpected request: ${path}`);
    });

    renderConsole("viewer");
    expect(await screen.findByText("High prompt injection blocked")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Load more incidents" }));
    expect(await screen.findByText("Second incident")).toBeVisible();
    expect(requests.some((path) => path.includes("cursor=next-page"))).toBe(true);
    expect(screen.queryByLabelText("Update incident status")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Incident assignee")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Plain-text comment")).not.toBeInTheDocument();
  });
});

function renderConsole(role: string) {
  return render(
    <QueryProvider>
      <IncidentConsole organizationId="org-1" role={role} csrfToken="csrf" />
    </QueryProvider>,
  );
}

function jsonResponse(body: object, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
