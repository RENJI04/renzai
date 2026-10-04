import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryProvider } from "@/shared/context/query-provider";
import { AIProviderConsole } from "./ai-provider-console";

describe("AI provider console", () => {
  afterEach(() => {
    cleanup();
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("keeps advisory content distinct and hides management controls from viewers", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ items: [provider] }));
    renderConsole("viewer");

    expect(await screen.findByText("Incident advisor")).toBeVisible();
    expect(screen.getByText("AI-generated")).toBeVisible();
    expect(screen.getByText("Provider management is restricted")).toBeVisible();
    expect(
      screen.queryByRole("heading", { name: "Update advisory provider" }),
    ).not.toBeInTheDocument();
  });

  it("submits a credential once without persisting it in browser storage", async () => {
    const requests: RequestInit[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      if (init?.method === "POST") requests.push(init);
      return init?.method === "POST" ? jsonResponse({}, 201) : jsonResponse({ items: [] });
    });
    renderConsole("owner");

    expect(await screen.findByText("No advisory provider configured")).toBeVisible();
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Incident advisor" } });
    fireEvent.change(screen.getByLabelText("Base URL"), {
      target: { value: "https://provider.example/v1" },
    });
    fireEvent.change(screen.getByLabelText("Model"), { target: { value: "secure-model" } });
    fireEvent.change(screen.getByLabelText("AI provider credential"), {
      target: { value: "transient-secret" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add provider" }));

    await waitFor(() => expect(requests).toHaveLength(1));
    expect(requests[0].headers).toMatchObject({ "X-Renzai-CSRF": "csrf-test" });
    expect(JSON.parse(String(requests[0].body))).toMatchObject({
      name: "Incident advisor",
      model: "secure-model",
      credential: "transient-secret",
    });
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });
});

const provider = {
  config_id: "config-1",
  application_id: null,
  environment_id: null,
  name: "Incident advisor",
  kind: "openai_compatible_remote",
  base_url: "https://provider.example/v1",
  model: "secure-model",
  credential_present: true,
  allow_full_content: false,
  status: "active",
  connect_timeout_seconds: 3,
  request_timeout_seconds: 30,
  response_max_bytes: 65536,
  updated_at: "2026-10-04T00:00:00Z",
};

function renderConsole(role: string) {
  return render(
    <QueryProvider>
      <AIProviderConsole organizationId="org-1" role={role} csrfToken="csrf-test" />
    </QueryProvider>,
  );
}

function jsonResponse(body: object, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
