import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QueryProvider } from "@/shared/context/query-provider";
import HomePage from "./page";

describe("identity page", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("announces loading and password-reset feedback to assistive technology", async () => {
    let sessionResolved = false;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith("/auth/session") && !sessionResolved) {
        sessionResolved = true;
        await new Promise((resolve) => setTimeout(resolve, 0));
        return errorResponse("authentication", "Authentication is required.", 401);
      }
      if (path.endsWith("/auth/password/reset/request") && init?.method === "POST") {
        return jsonResponse({ accepted: true }, 202);
      }
      throw new Error(`Unexpected request: ${path}`);
    });
    render(
      <QueryProvider>
        <HomePage />
      </QueryProvider>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Loading your workspace");
    fireEvent.click(await screen.findByRole("button", { name: "Forgot your password?" }));
    fireEvent.change(screen.getByLabelText("Email"), {
      target: { value: "reset@example.test" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Request reset" }).closest("form")!);
    expect(await screen.findByRole("status")).toHaveTextContent(
      "If that account exists, password reset instructions are ready.",
    );
  });

  it("shows the sign-in experience when there is no session", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "authentication",
            message: "Authentication is required.",
            request_id: "test",
          },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      ),
    );
    render(
      <QueryProvider>
        <HomePage />
      </QueryProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });

  it("registers and re-bootstraps the authenticated session", async () => {
    let authenticated = false;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith("/auth/register") && init?.method === "POST") {
        authenticated = true;
        return jsonResponse({ user: { email: "new@example.com" } }, 201);
      }
      if (path.endsWith("/auth/session")) {
        return authenticated
          ? jsonResponse(sessionFixture())
          : errorResponse("authentication", "Authentication is required.", 401);
      }
      if (path.endsWith("/organizations")) return jsonResponse({ items: [] });
      throw new Error(`Unexpected request: ${path}`);
    });
    render(
      <QueryProvider>
        <HomePage />
      </QueryProvider>,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Need an account? Register" }));
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "new@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "correct horse 12345" },
    });
    fireEvent.submit(screen.getByRole("button", { name: "Register" }).closest("form")!);
    expect(await screen.findByText("new@example.com")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Create your first organization" })).toBeVisible();
  });

  it("switches tenants, applies role-aware controls, and clears the session on logout", async () => {
    let authenticated = true;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const path = String(input);
      if (path.endsWith("/auth/logout") && init?.method === "POST") {
        authenticated = false;
        return new Response(null, { status: 204 });
      }
      if (path.endsWith("/auth/session")) {
        return authenticated
          ? jsonResponse(sessionFixture())
          : errorResponse("authentication", "Authentication is required.", 401);
      }
      if (path.endsWith("/organizations")) {
        return jsonResponse({
          items: [
            {
              organization_id: "org-a",
              membership_id: "member-a",
              name: "Alpha",
              slug: "alpha",
              role: "owner",
            },
            {
              organization_id: "org-b",
              membership_id: "member-b",
              name: "Beta",
              slug: "beta",
              role: "viewer",
            },
          ],
        });
      }
      if (path.includes("/applications")) return jsonResponse({ items: [] });
      if (path.includes("/members")) return jsonResponse({ items: [] });
      throw new Error(`Unexpected request: ${path}`);
    });
    render(
      <QueryProvider>
        <HomePage />
      </QueryProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Alpha" })).toBeVisible();
    fireEvent.click(screen.getByText("New organization"));
    expect(screen.getByLabelText("Organization name")).toBeVisible();
    expect(screen.getByLabelText("Organization slug")).toBeVisible();
    fireEvent.click(screen.getByText("Accept invitation"));
    expect(screen.getByLabelText("Invitation token")).toBeVisible();
    expect(screen.getByLabelText("Invitee email")).toBeVisible();
    expect(screen.getByLabelText("Invitation role")).toBeVisible();
    expect(screen.getByLabelText("Current password")).toBeVisible();
    expect(screen.getByLabelText("New password")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Invite a member" })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: /Beta/ }));
    expect(await screen.findByRole("heading", { name: "Beta" })).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Invite a member" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign out" }));
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Welcome back" })).toBeVisible(),
    );
  });
});

function jsonResponse(body: object, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function errorResponse(code: string, message: string, status: number): Response {
  return jsonResponse({ error: { code, message, request_id: "test" } }, status);
}

function sessionFixture() {
  return {
    user: {
      user_id: "user-1",
      email: "new@example.com",
      status: "active",
      email_verified: false,
    },
    csrf_token: "csrf-token",
    memberships: [],
  };
}
