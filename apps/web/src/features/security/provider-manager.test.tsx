import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryProvider } from "@/shared/context/query-provider";
import { ProviderManager } from "./provider-manager";

describe("provider manager assurance states", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("announces loading and exposes labeled owner controls", async () => {
    let resolveRequest: ((response: Response) => void) | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          resolveRequest = resolve;
        }),
    );
    renderManager("owner");
    expect(screen.getByRole("status")).toHaveTextContent("Loading provider configurations");
    resolveRequest?.(jsonResponse({ items: [] }));
    expect(await screen.findByText("No provider configurations yet.")).toBeVisible();
    expect(screen.getByLabelText("Kind")).toBeVisible();
    expect(screen.getByLabelText("Name")).toBeVisible();
    expect(screen.getByLabelText("Base URL")).toBeVisible();
    expect(screen.getByLabelText("Model")).toBeVisible();
    expect(screen.getByLabelText("Provider credential")).toBeVisible();
    expect(screen.getByLabelText("Maximum tokens")).toBeVisible();
  });

  it("renders read failures as alerts without exposing management to viewers", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      jsonResponse(
        {
          error: {
            code: "configuration_error",
            message: "The service is not configured.",
            request_id: "provider-read-test",
          },
        },
        503,
      ),
    );
    renderManager("viewer");
    expect(await screen.findByRole("alert", undefined, { timeout: 3_000 })).toHaveTextContent(
      "The service is not configured. (provider-read-test)",
    );
    expect(screen.queryByRole("heading", { name: "Create provider" })).not.toBeInTheDocument();
  });
});

function renderManager(role: string) {
  return render(
    <QueryProvider>
      <ProviderManager
        organizationId="org-1"
        applicationId="app-1"
        environmentId="env-1"
        role={role}
        csrfToken="csrf-test"
      />
    </QueryProvider>,
  );
}

function jsonResponse(body: object, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
