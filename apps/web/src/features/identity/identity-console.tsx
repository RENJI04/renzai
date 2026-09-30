"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, RenzaiApiError } from "@/shared/api/client";
import { SecurityConsole } from "@/features/security/security-console";

type Membership = { organization_id: string; membership_id: string; role: string };
type Session = {
  user: { user_id: string; email: string; status: string; email_verified: boolean };
  csrf_token: string;
  memberships: Membership[];
};
type Organization = {
  organization_id: string;
  membership_id: string;
  name: string;
  slug: string;
  role: string;
};
type Member = { membership_id: string; email: string; role: string; status: string };

const json = (body: object): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function errorText(error: unknown): string {
  if (error instanceof RenzaiApiError) return `${error.message} (${error.requestId})`;
  return error instanceof Error ? error.message : "Something went wrong.";
}

export function IdentityConsole() {
  const queryClient = useQueryClient();
  const sessionQuery = useQuery({
    queryKey: ["session"],
    queryFn: () => apiRequest<Session>("/api/v1/auth/session"),
    retry: false,
  });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["session"] });
    await queryClient.invalidateQueries({ queryKey: ["organizations"] });
  };
  const clearSession = () => {
    queryClient.setQueryData<Session | null>(["session"], null);
    queryClient.removeQueries({ queryKey: ["organizations"] });
    queryClient.removeQueries({ queryKey: ["members"] });
  };

  if (sessionQuery.isPending) {
    return (
      <main className="centered">
        <p>Loading your workspace…</p>
      </main>
    );
  }
  if (!sessionQuery.data) return <AuthCard onAuthenticated={refresh} />;
  return <Workspace session={sessionQuery.data} onLoggedOut={clearSession} />;
}

function AuthCard({ onAuthenticated }: { onAuthenticated: () => Promise<void> }) {
  const [mode, setMode] = useState<"login" | "register" | "reset">("login");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const mutation = useMutation({
    mutationFn: async (form: FormData) => {
      if (mode === "reset") {
        return apiRequest(
          "/api/v1/auth/password/reset/request",
          json({ email: form.get("email") }),
        );
      }
      const endpoint = mode === "login" ? "login" : "register";
      return apiRequest(
        `/api/v1/auth/${endpoint}`,
        json({ email: form.get("email"), password: form.get("password") }),
      );
    },
    onSuccess: async () => {
      if (mode === "reset") {
        setNotice("If that account exists, password reset instructions are ready.");
        return;
      }
      await onAuthenticated();
    },
    onError: (failure) => setError(errorText(failure)),
  });
  return (
    <main className="centered">
      <section className="auth-card" aria-labelledby="auth-heading">
        <div className="brand-mark">R</div>
        <p className="eyebrow">RENZAI</p>
        <h1 id="auth-heading">
          {mode === "login"
            ? "Welcome back"
            : mode === "register"
              ? "Create your account"
              : "Reset your password"}
        </h1>
        <p className="muted">Identity and organization access for the AI security platform.</p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate(new FormData(event.currentTarget));
          }}
        >
          <label>
            Email
            <input name="email" type="email" autoComplete="email" required />
          </label>
          {mode !== "reset" && (
            <label>
              Password
              <input
                name="password"
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={12}
                required
              />
            </label>
          )}
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button className="primary" disabled={mutation.isPending}>
            {mutation.isPending
              ? "Working…"
              : mode === "login"
                ? "Sign in"
                : mode === "register"
                  ? "Register"
                  : "Request reset"}
          </button>
        </form>
        {notice && <p className="notice">{notice}</p>}
        <button
          className="text-button"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login");
            setError("");
            setNotice("");
          }}
        >
          {mode === "login" ? "Need an account? Register" : "Back to sign in"}
        </button>
        {mode === "login" && (
          <button className="text-button" onClick={() => setMode("reset")}>
            Forgot your password?
          </button>
        )}
      </section>
    </main>
  );
}

function Workspace({ session, onLoggedOut }: { session: Session; onLoggedOut: () => void }) {
  const queryClient = useQueryClient();
  const organizations = useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiRequest<{ items: Organization[] }>("/api/v1/organizations"),
  });
  const [activeId, setActiveId] = useState<string | null>(null);
  const active =
    organizations.data?.items.find((item) => item.organization_id === activeId) ??
    organizations.data?.items[0];
  const canManage = active?.role === "owner" || active?.role === "admin";
  const members = useQuery({
    queryKey: ["members", active?.organization_id],
    queryFn: () =>
      apiRequest<{ items: Member[] }>(`/api/v1/organizations/${active?.organization_id}/members`),
    enabled: Boolean(active && canManage),
  });
  const [error, setError] = useState("");
  const mutate = useMutation({
    mutationFn: async ({ path, init }: { path: string; init: RequestInit }) =>
      apiRequest(path, init, session.csrf_token),
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries();
    },
    onError: (failure) => setError(errorText(failure)),
  });
  const submit = (
    event: FormEvent<HTMLFormElement>,
    action: (form: FormData) => { path: string; init: RequestInit },
  ) => {
    event.preventDefault();
    mutate.mutate(action(new FormData(event.currentTarget)));
    event.currentTarget.reset();
  };
  return (
    <main className="workspace">
      <header className="topbar">
        <div>
          <span className="logo">Renzai</span>
          <span className="phase">Provider Gateway · Phase 8</span>
        </div>
        <div className="account">
          <span>{session.user.email}</span>
          <button
            onClick={async () => {
              await apiRequest("/api/v1/auth/logout", { method: "POST" }, session.csrf_token);
              onLoggedOut();
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <div className="workspace-grid">
        <aside>
          <p className="eyebrow">ORGANIZATIONS</p>
          <nav aria-label="Organizations">
            {organizations.data?.items.map((organization) => (
              <button
                key={organization.organization_id}
                className={organization.organization_id === active?.organization_id ? "active" : ""}
                onClick={() => setActiveId(organization.organization_id)}
              >
                <span>{organization.name}</span>
                <small>{organization.role}</small>
              </button>
            ))}
          </nav>
          <details>
            <summary>New organization</summary>
            <form
              onSubmit={(event) =>
                submit(event, (form) => ({
                  path: "/api/v1/organizations",
                  init: json({ name: form.get("name"), slug: form.get("slug") }),
                }))
              }
            >
              <input name="name" placeholder="Organization name" required />
              <input name="slug" placeholder="organization-slug" required />
              <button className="primary">Create</button>
            </form>
          </details>
          <details>
            <summary>Accept invitation</summary>
            <form
              onSubmit={(event) =>
                submit(event, (form) => ({
                  path: `/api/v1/invitations/${String(form.get("token"))}/accept`,
                  init: { method: "POST" },
                }))
              }
            >
              <input name="token" placeholder="rziv_…" required />
              <button className="primary">Accept</button>
            </form>
          </details>
        </aside>
        <section className="content">
          {active ? (
            <>
              <p className="eyebrow">{active.role.toUpperCase()}</p>
              <h1>{active.name}</h1>
              <p className="muted">Tenant ID: {active.organization_id}</p>
              {canManage && (
                <section className="panel">
                  <h2>Members</h2>
                  <div className="member-list">
                    {members.data?.items.map((member) => (
                      <div key={member.membership_id}>
                        <span>{member.email}</span>
                        <span className="member-actions">
                          <select
                            aria-label={`Role for ${member.email}`}
                            value={member.role}
                            onChange={(event) =>
                              mutate.mutate({
                                path: `/api/v1/organizations/${active.organization_id}/members/${member.membership_id}`,
                                init: {
                                  ...json({ role: event.target.value }),
                                  method: "PATCH",
                                },
                              })
                            }
                          >
                            <option value="viewer">Viewer</option>
                            <option value="developer">Developer</option>
                            <option value="security_analyst">Security analyst</option>
                            <option value="admin">Admin</option>
                            {active.role === "owner" && <option value="owner">Owner</option>}
                          </select>
                          <button
                            aria-label={`Remove ${member.email}`}
                            onClick={() =>
                              mutate.mutate({
                                path: `/api/v1/organizations/${active.organization_id}/members/${member.membership_id}`,
                                init: { method: "DELETE" },
                              })
                            }
                          >
                            Remove
                          </button>
                        </span>
                      </div>
                    ))}
                  </div>
                  <h3>Invite a member</h3>
                  <form
                    className="inline-form"
                    onSubmit={(event) =>
                      submit(event, (form) => ({
                        path: `/api/v1/organizations/${active.organization_id}/invitations`,
                        init: json({ email: form.get("email"), role: form.get("role") }),
                      }))
                    }
                  >
                    <input name="email" type="email" placeholder="person@example.com" required />
                    <select name="role" defaultValue="viewer">
                      <option value="viewer">Viewer</option>
                      <option value="developer">Developer</option>
                      <option value="security_analyst">Security analyst</option>
                      <option value="admin">Admin</option>
                      {active.role === "owner" && <option value="owner">Owner</option>}
                    </select>
                    <button className="primary">Invite</button>
                  </form>
                </section>
              )}
            </>
          ) : (
            <section className="empty">
              <h1>Create your first organization</h1>
              <p className="muted">
                Organizations are the isolation boundary for every Renzai resource.
              </p>
            </section>
          )}
          {active && (
            <SecurityConsole
              key={active.organization_id}
              organizationId={active.organization_id}
              role={active.role}
              csrfToken={session.csrf_token}
            />
          )}
          <section className="panel">
            <h2>Account security</h2>
            <div className="actions">
              <button
                onClick={() =>
                  mutate.mutate({
                    path: "/api/v1/auth/email/verification/request",
                    init: { method: "POST" },
                  })
                }
                disabled={session.user.email_verified}
              >
                {session.user.email_verified ? "Email verified" : "Send verification"}
              </button>
            </div>
            <form
              className="inline-form"
              onSubmit={(event) =>
                submit(event, (form) => ({
                  path: "/api/v1/auth/password/change",
                  init: json({
                    current_password: form.get("current_password"),
                    new_password: form.get("new_password"),
                  }),
                }))
              }
            >
              <input
                name="current_password"
                type="password"
                autoComplete="current-password"
                placeholder="Current password"
                required
              />
              <input
                name="new_password"
                type="password"
                autoComplete="new-password"
                placeholder="New password"
                minLength={12}
                required
              />
              <button className="primary">Change password</button>
            </form>
          </section>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
        </section>
      </div>
    </main>
  );
}
