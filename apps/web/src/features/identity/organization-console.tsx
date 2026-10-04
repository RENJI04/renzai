"use client";

import Image from "next/image";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { EnvelopeSimpleIcon, PlusIcon, UsersThreeIcon } from "@phosphor-icons/react";
import { apiRequest, RenzaiApiError } from "@/shared/api/client";
import type { Member, Organization, Session } from "./types";

const json = (body: object, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function errorText(error: unknown): string {
  if (error instanceof RenzaiApiError) return `${error.message} (${error.requestId})`;
  return error instanceof Error ? error.message : "Organization operation failed.";
}

export function OrganizationConsole({
  active,
  session,
}: {
  active: Organization;
  session: Session;
}) {
  const queryClient = useQueryClient();
  const canManage = active.role === "owner" || active.role === "admin";
  const [error, setError] = useState("");
  const members = useQuery({
    queryKey: ["members", active.organization_id],
    queryFn: () =>
      apiRequest<{ items: Member[] }>(`/api/v1/organizations/${active.organization_id}/members`),
    enabled: canManage,
  });
  const mutate = useMutation({
    mutationFn: ({ path, init }: { path: string; init: RequestInit }) =>
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
    <div className="page-stack">
      <section className="surface-card organization-summary">
        <div className="section-heading">
          <div className="icon-tile">
            <UsersThreeIcon size={22} weight="duotone" aria-hidden="true" />
          </div>
          <div>
            <h2>{active.name}</h2>
            <p>Tenant ID {active.organization_id}</p>
          </div>
        </div>
        <span className="badge badge-accent">{active.role.replace("_", " ")}</span>
      </section>

      {canManage ? (
        <section className="surface-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Access control</p>
              <h2>Members</h2>
              <p>Roles determine the controls available inside this organization.</p>
            </div>
          </div>
          {members.isPending ? (
            <div className="inline-skeleton" role="status">
              Loading members…
            </div>
          ) : null}
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Member</th>
                  <th>Status</th>
                  <th>Role</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {members.data?.items.map((member) => (
                  <tr key={member.membership_id}>
                    <td>
                      <strong>{member.email}</strong>
                    </td>
                    <td>
                      <span className="badge badge-neutral">{member.status}</span>
                    </td>
                    <td>
                      <select
                        aria-label={`Role for ${member.email}`}
                        value={member.role}
                        onChange={(event) =>
                          mutate.mutate({
                            path: `/api/v1/organizations/${active.organization_id}/members/${member.membership_id}`,
                            init: json({ role: event.target.value }, "PATCH"),
                          })
                        }
                      >
                        <option value="viewer">Viewer</option>
                        <option value="developer">Developer</option>
                        <option value="security_analyst">Security analyst</option>
                        <option value="admin">Admin</option>
                        {active.role === "owner" && <option value="owner">Owner</option>}
                      </select>
                    </td>
                    <td className="table-action">
                      <button
                        className="button button-danger-quiet"
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
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <form
            className="compact-form"
            onSubmit={(event) =>
              submit(event, (form) => ({
                path: `/api/v1/organizations/${active.organization_id}/invitations`,
                init: json({ email: form.get("email"), role: form.get("role") }),
              }))
            }
          >
            <div className="form-heading">
              <EnvelopeSimpleIcon size={20} aria-hidden="true" />
              <div>
                <h3>Invite a member</h3>
                <p>Send tenant-scoped access with the minimum required role.</p>
              </div>
            </div>
            <div className="inline-form">
              <input
                aria-label="Invitee email"
                name="email"
                type="email"
                placeholder="person@company.com"
                required
              />
              <select aria-label="Invitation role" name="role" defaultValue="viewer">
                <option value="viewer">Viewer</option>
                <option value="developer">Developer</option>
                <option value="security_analyst">Security analyst</option>
                <option value="admin">Admin</option>
                {active.role === "owner" && <option value="owner">Owner</option>}
              </select>
              <button className="button button-primary">
                <PlusIcon size={17} aria-hidden="true" />
                Invite
              </button>
            </div>
          </form>
        </section>
      ) : (
        <section className="state-card">
          <UsersThreeIcon size={28} weight="duotone" aria-hidden="true" />
          <h2>Member administration is restricted</h2>
          <p>
            Your {active.role.replace("_", " ")} role can view the workspace but cannot manage
            organization membership.
          </p>
        </section>
      )}

      <section className="surface-card two-column-actions">
        <form
          onSubmit={(event) =>
            submit(event, (form) => ({
              path: "/api/v1/organizations",
              init: json({ name: form.get("name"), slug: form.get("slug") }),
            }))
          }
        >
          <h3>Create another organization</h3>
          <p className="muted">Create a separate tenant boundary.</p>
          <input
            aria-label="Organization name"
            name="name"
            placeholder="Organization name"
            required
          />
          <input
            aria-label="Organization slug"
            name="slug"
            placeholder="organization-slug"
            required
          />
          <button className="button button-secondary">Create organization</button>
        </form>
        <form
          onSubmit={(event) =>
            submit(event, (form) => ({
              path: `/api/v1/invitations/${String(form.get("token"))}/accept`,
              init: { method: "POST" },
            }))
          }
        >
          <h3>Accept an invitation</h3>
          <p className="muted">Use the complete invitation token you received.</p>
          <input aria-label="Invitation token" name="token" placeholder="rziv_…" required />
          <button className="button button-secondary">Accept invitation</button>
        </form>
      </section>
      {error && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

export function OrganizationOnboarding({ session }: { session: Session }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState("");
  const mutate = useMutation({
    mutationFn: ({ path, init }: { path: string; init: RequestInit }) =>
      apiRequest(path, init, session.csrf_token),
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["organizations"] });
    },
    onError: (failure) => setError(errorText(failure)),
  });
  const submit = (
    event: FormEvent<HTMLFormElement>,
    action: (form: FormData) => { path: string; init: RequestInit },
  ) => {
    event.preventDefault();
    mutate.mutate(action(new FormData(event.currentTarget)));
  };
  return (
    <main className="onboarding-shell">
      <section className="onboarding-card">
        <Image src="/brand/renzai-logo.png" width={150} height={150} alt="Renzai" />
        <p className="eyebrow">Workspace setup</p>
        <h1>Create your first organization</h1>
        <p className="page-summary">
          Organizations are the isolation boundary for every Renzai resource. You can also join an
          existing tenant with an invitation.
        </p>
        <div className="onboarding-options">
          <form
            onSubmit={(event) =>
              submit(event, (form) => ({
                path: "/api/v1/organizations",
                init: json({ name: form.get("name"), slug: form.get("slug") }),
              }))
            }
          >
            <h2>New organization</h2>
            <label>
              Organization name
              <input
                aria-label="Organization name"
                name="name"
                placeholder="Acme Security"
                required
              />
            </label>
            <label>
              URL slug
              <input
                aria-label="Organization slug"
                name="slug"
                placeholder="acme-security"
                required
              />
            </label>
            <button className="button button-primary" disabled={mutate.isPending}>
              Create secure workspace
            </button>
          </form>
          <div className="onboarding-divider">
            <span>or</span>
          </div>
          <form
            onSubmit={(event) =>
              submit(event, (form) => ({
                path: `/api/v1/invitations/${String(form.get("token"))}/accept`,
                init: { method: "POST" },
              }))
            }
          >
            <h2>Join your team</h2>
            <label>
              Invitation token
              <input aria-label="Invitation token" name="token" placeholder="rziv_…" required />
            </label>
            <button className="button button-secondary" disabled={mutate.isPending}>
              Accept invitation
            </button>
          </form>
        </div>
        {error && (
          <p className="alert alert-error" role="alert">
            {error}
          </p>
        )}
        <p className="auth-security-note">Signed in as {session.user.email}</p>
      </section>
    </main>
  );
}
