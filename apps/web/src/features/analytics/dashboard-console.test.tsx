import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryProvider } from "@/shared/context/query-provider";
import { DashboardConsole } from "./dashboard-console";

vi.mock("./dashboard-charts", () => ({
  ActivityChart: ({ data }: { data: Array<{ analysis_count: number }> }) => (
    <div data-testid="activity-chart-data">
      analyses={data.reduce((total, item) => total + item.analysis_count, 0)}
    </div>
  ),
  MetricBarChart: ({ label }: { label: string }) => <div>{label} chart</div>,
}));

const activity = Array.from({ length: 24 }, (_, index) => ({
  bucket_start: `2026-10-01T${String(index).padStart(2, "0")}:00:00+00:00`,
  analysis_count: index === 12 ? 10 : 0,
  threat_count: index === 12 ? 4 : 0,
  blocked_count: index === 12 ? 1 : 0,
  review_count: index === 12 ? 1 : 0,
}));
const dashboard = {
  filters: {
    window: "24h",
    window_start: "2026-10-01T00:00:00+00:00",
    window_end: "2026-10-01T23:59:00+00:00",
    bucket: "hour",
  },
  summary: {
    analyses: 10,
    gateway_requests: 7,
    threats_detected: 4,
    blocked: 1,
    require_review: 1,
    redacted: 1,
    critical_analyses: 2,
    open_incidents: 1,
    threat_rate_numerator: 4,
    threat_rate_denominator: 10,
    threat_rate_percent: 40,
  },
  activity,
  risk_distribution: [
    { severity: "low", count: 4 },
    { severity: "medium", count: 2 },
    { severity: "high", count: 2 },
    { severity: "critical", count: 2 },
  ],
  threat_categories: [{ category: "prompt_injection", finding_count: 3, affected_analyses: 2 }],
  top_detectors: [
    {
      detector_id: "prompt-injection",
      detector_version: "1.0.0",
      finding_count: 3,
      affected_analyses: 2,
      average_confidence: 91,
    },
  ],
  policy_actions: [
    { action: "allow", count: 6 },
    { action: "flag", count: 1 },
    { action: "redact", count: 1 },
    { action: "require_review", count: 1 },
    { action: "block", count: 1 },
  ],
  applications: [],
  environments: [],
  providers: [
    {
      provider_id: "provider-1",
      provider_name: "Local provider",
      configured_model: "safe-model",
      request_count: 7,
      completed: 1,
      provider_timeout: 1,
      provider_error: 1,
      configuration_error: 1,
      output_block: 1,
      output_review: 1,
      output_inspection_failure: 1,
      average_latency_ms: 43,
    },
  ],
  incidents: {
    statuses: [
      { status: "open", count: 1 },
      { status: "investigating", count: 1 },
      { status: "resolved", count: 1 },
      { status: "ignored", count: 1 },
      { status: "false_positive", count: 1 },
    ],
    critical_open: 1,
    unassigned_open: 1,
  },
  recent_incidents: [
    {
      incident_id: "incident-1",
      status: "open",
      severity: "critical",
      category: "prompt_injection",
      action: "block",
      created_at: "2026-10-01T12:00:00Z",
    },
  ],
  query_duration_ms: 8,
};

describe("dashboard console", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders KPIs, accessible chart values, provider usage, and incident status", async () => {
    mockDashboard(dashboard);
    renderConsole("org-1");

    expect(await screen.findByText("40%")).toBeVisible();
    expect(screen.getByText("Local provider")).toBeVisible();
    expect(screen.getByText("safe-model")).toBeVisible();
    expect(screen.getByText("False positive")).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "Recent incidents" }).parentElement,
    ).toHaveTextContent("Critical · Prompt injection · Block");
    expect(screen.getByTestId("activity-chart-data")).toHaveTextContent("analyses=10");
    expect(
      screen.getByRole("img", {
        name: "Analyses, threats, blocked, and review activity over time",
      }),
    ).toBeVisible();
    expect(screen.getByText("Threat category values")).toBeInTheDocument();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("propagates every global filter and clears environment when application changes", async () => {
    const requests = mockDashboard(dashboard);
    renderConsole("org-1");
    expect(await screen.findByText("40%")).toBeVisible();

    fireEvent.change(screen.getByLabelText("Dashboard window"), { target: { value: "7d" } });
    fireEvent.change(screen.getByLabelText("Dashboard application"), {
      target: { value: "app-1" },
    });
    expect(await screen.findByRole("option", { name: "production" })).toBeVisible();
    fireEvent.change(screen.getByLabelText("Dashboard environment"), {
      target: { value: "env-1" },
    });
    fireEvent.change(screen.getByLabelText("Dashboard source"), {
      target: { value: "gateway" },
    });
    await waitFor(() =>
      expect(
        requests.some(
          (path) =>
            path.includes("window=7d") &&
            path.includes("application_id=app-1") &&
            path.includes("environment_id=env-1") &&
            path.includes("source=gateway"),
        ),
      ).toBe(true),
    );
    fireEvent.change(screen.getByLabelText("Dashboard application"), {
      target: { value: "app-2" },
    });
    expect(screen.getByLabelText("Dashboard environment")).toHaveValue("");
  });

  it("renders a truthful empty state instead of treating zero as loading", async () => {
    mockDashboard({
      ...dashboard,
      summary: Object.fromEntries(
        Object.keys(dashboard.summary).map((key) => [key, 0]),
      ) as typeof dashboard.summary,
      providers: [],
    });
    renderConsole("org-empty");
    expect(await screen.findByText("No security activity in this period")).toBeVisible();
    expect(screen.getByText("No Gateway provider calls.")).toBeVisible();
  });

  it("shows a safe error and includes organization identity in every query", async () => {
    const requests: string[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const path = String(input);
      requests.push(path);
      if (path.endsWith("/applications")) return jsonResponse({ items: [] });
      return new Response("database stack trace", { status: 500 });
    });
    renderConsole("org-private");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Dashboard data could not be loaded.",
    );
    expect(screen.queryByText(/database stack trace/i)).not.toBeInTheDocument();
    expect(requests.every((path) => path.includes("org-private"))).toBe(true);
  });
});

function renderConsole(organizationId: string) {
  return render(
    <QueryProvider>
      <DashboardConsole key={organizationId} organizationId={organizationId} />
    </QueryProvider>,
  );
}

function mockDashboard(body: typeof dashboard): string[] {
  const requests: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    requests.push(path);
    if (path.endsWith("/applications"))
      return jsonResponse({
        items: [
          { application_id: "app-1", name: "Assistant" },
          { application_id: "app-2", name: "Copilot" },
        ],
      });
    if (path.includes("/applications/app-1/environments"))
      return jsonResponse({ items: [{ environment_id: "env-1", type: "production" }] });
    if (path.includes("/applications/app-2/environments")) return jsonResponse({ items: [] });
    if (path.includes("/analytics/dashboard?")) return jsonResponse(body);
    throw new Error(`Unexpected request: ${path}`);
  });
  return requests;
}

function jsonResponse(body: object): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
