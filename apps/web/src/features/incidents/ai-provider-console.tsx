"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BrainIcon,
  LockKeyIcon,
  PlugsConnectedIcon,
  WarningCircleIcon,
} from "@phosphor-icons/react";
import { apiRequest, RenzaiApiError } from "@/shared/api/client";

type AIProvider = {
  config_id: string;
  application_id: string | null;
  environment_id: string | null;
  name: string;
  kind: "openai_compatible_remote" | "openai_compatible_local";
  base_url: string;
  model: string;
  credential_present: boolean;
  allow_full_content: boolean;
  status: "active" | "disabled";
  connect_timeout_seconds: number;
  request_timeout_seconds: number;
  response_max_bytes: number;
  updated_at: string;
};

const json = (body: object, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function message(error: unknown): string {
  if (error instanceof RenzaiApiError) return `${error.message} (${error.requestId})`;
  return error instanceof Error ? error.message : "AI provider operation failed.";
}

export function AIProviderConsole({
  organizationId,
  role,
  csrfToken,
}: {
  organizationId: string;
  role: string;
  csrfToken: string;
}) {
  const queryClient = useQueryClient();
  const canManage = role === "owner" || role === "admin";
  const path = `/api/v1/organizations/${organizationId}/ai-providers`;
  const [editing, setEditing] = useState<AIProvider | null>(null);
  const [credential, setCredential] = useState("");
  const [kind, setKind] = useState<AIProvider["kind"]>("openai_compatible_remote");
  const [error, setError] = useState("");
  const providers = useQuery({
    queryKey: ["ai-providers", organizationId],
    queryFn: () => apiRequest<{ items: AIProvider[] }>(path),
  });
  const action = useMutation({
    mutationFn: ({
      configId,
      operation,
    }: {
      configId: string;
      operation: "enable" | "disable" | "validate";
    }) => apiRequest(`${path}/${configId}/${operation}`, { method: "POST" }, csrfToken),
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["ai-providers", organizationId] });
    },
    onError: (failure) => setError(message(failure)),
  });
  const save = useMutation({
    mutationFn: async ({
      body,
      configId,
    }: {
      body: Record<string, unknown>;
      configId?: string;
    }) => {
      await apiRequest(
        configId ? `${path}/${configId}` : path,
        json(body, configId ? "PATCH" : "POST"),
        csrfToken,
      );
    },
    onSuccess: async () => {
      setCredential("");
      setEditing(null);
      setKind("openai_compatible_remote");
      setError("");
      await queryClient.invalidateQueries({ queryKey: ["ai-providers", organizationId] });
    },
    onError: (failure) => setError(message(failure)),
  });

  function submitProvider(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body: Record<string, unknown> = {
      name: form.get("name"),
      model: form.get("model"),
      allow_full_content: form.get("allow_full_content") === "on",
    };
    if (!editing) {
      body.kind = kind;
      body.base_url = form.get("base_url");
      body.connect_timeout_seconds = 3;
      body.request_timeout_seconds = 30;
      body.response_max_bytes = 65536;
    }
    if (credential) body.credential = credential;
    save.mutate({ body, configId: editing?.config_id });
  }

  return (
    <div className="page-stack">
      <section className="advisory-banner">
        <BrainIcon size={24} weight="duotone" aria-hidden="true" />
        <div>
          <strong>Advisory by design</strong>
          <p>
            AI Intelligence can summarize and suggest within an incident. It never replaces
            deterministic findings or changes policy enforcement.
          </p>
        </div>
        <span className="badge badge-ai">AI-generated</span>
      </section>

      <section className="surface-card">
        <div className="section-heading section-heading-split">
          <div>
            <p className="eyebrow">Provider inventory</p>
            <h2>Advisory connections</h2>
            <p>Credentials are encrypted at rest and never displayed after submission.</p>
          </div>
          <span className="metric-pill">
            <PlugsConnectedIcon size={17} aria-hidden="true" />
            {providers.data?.items.length ?? 0} configured
          </span>
        </div>
        {providers.isPending && (
          <div className="loading-state" role="status">
            <span className="spinner" />
            Loading AI providers…
          </div>
        )}
        {providers.isError && (
          <p className="alert alert-error" role="alert">
            {message(providers.error)}
          </p>
        )}
        {providers.data?.items.length === 0 && (
          <div className="empty-state">
            <BrainIcon size={30} weight="duotone" aria-hidden="true" />
            <h3>No advisory provider configured</h3>
            <p>Add an OpenAI-compatible endpoint to enable incident-scoped advisory tasks.</p>
          </div>
        )}
        <div className="provider-grid">
          {providers.data?.items.map((provider) => (
            <article className="provider-card" key={provider.config_id}>
              <header>
                <div className="icon-tile">
                  <BrainIcon size={20} weight="duotone" aria-hidden="true" />
                </div>
                <div>
                  <h3>{provider.name}</h3>
                  <p>{provider.model}</p>
                </div>
                <span
                  className={`badge ${provider.status === "active" ? "badge-success" : "badge-neutral"}`}
                >
                  {provider.status}
                </span>
              </header>
              <dl className="compact-facts">
                <div>
                  <dt>Endpoint</dt>
                  <dd>{provider.base_url}</dd>
                </div>
                <div>
                  <dt>Credential</dt>
                  <dd>{provider.credential_present ? "Encrypted" : "Not configured"}</dd>
                </div>
                <div>
                  <dt>Disclosure</dt>
                  <dd>
                    {provider.allow_full_content ? "Full content allowed" : "Redacted / metadata"}
                  </dd>
                </div>
                <div>
                  <dt>Updated</dt>
                  <dd>{new Date(provider.updated_at).toLocaleDateString()}</dd>
                </div>
              </dl>
              {canManage && (
                <div className="actions">
                  <button
                    className="button button-quiet"
                    onClick={() => {
                      setEditing(provider);
                      setKind(provider.kind);
                      setCredential("");
                    }}
                  >
                    Edit
                  </button>
                  <button
                    className="button button-quiet"
                    onClick={() =>
                      action.mutate({ configId: provider.config_id, operation: "validate" })
                    }
                  >
                    Validate
                  </button>
                  <button
                    className="button button-quiet"
                    onClick={() =>
                      action.mutate({
                        configId: provider.config_id,
                        operation: provider.status === "active" ? "disable" : "enable",
                      })
                    }
                  >
                    {provider.status === "active" ? "Disable" : "Enable"}
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      </section>

      {canManage ? (
        <section className="surface-card form-surface">
          <div className="section-heading">
            <div className="icon-tile">
              <LockKeyIcon size={21} weight="duotone" aria-hidden="true" />
            </div>
            <div>
              <h2>{editing ? "Update advisory provider" : "Add advisory provider"}</h2>
              <p>Secrets remain transient in this browser and are submitted once.</p>
            </div>
          </div>
          <form key={editing?.config_id ?? "create"} onSubmit={submitProvider}>
            <div className="form-grid">
              {!editing && (
                <label>
                  Provider type
                  <select
                    name="kind"
                    value={kind}
                    onChange={(event) => setKind(event.target.value as AIProvider["kind"])}
                  >
                    <option value="openai_compatible_remote">Remote OpenAI-compatible</option>
                    <option value="openai_compatible_local">Explicit local provider</option>
                  </select>
                </label>
              )}
              <label>
                Name
                <input name="name" defaultValue={editing?.name ?? ""} required />
              </label>
              {!editing && (
                <label className="field-wide">
                  Base URL
                  <input
                    name="base_url"
                    type="url"
                    defaultValue=""
                    placeholder="https://provider.example/v1"
                    required
                  />
                </label>
              )}
              <label>
                Model
                <input name="model" defaultValue={editing?.model ?? ""} required />
              </label>
              <label>
                Credential{" "}
                {editing && <span className="label-note">leave blank to keep current</span>}
                <input
                  aria-label="AI provider credential"
                  type="password"
                  autoComplete="new-password"
                  value={credential}
                  onChange={(event) => setCredential(event.target.value)}
                  required={!editing && kind === "openai_compatible_remote"}
                />
              </label>
            </div>
            <label className="checkbox-label">
              <input
                name="allow_full_content"
                type="checkbox"
                defaultChecked={editing?.allow_full_content ?? false}
              />
              <span>
                <strong>Allow full-content disclosure</strong>
                <small>Availability remains constrained by role and incident privacy mode.</small>
              </span>
            </label>
            <div className="actions">
              <button className="button button-primary" disabled={save.isPending}>
                {save.isPending ? "Saving…" : editing ? "Save provider" : "Add provider"}
              </button>
              {editing && (
                <button
                  type="button"
                  className="button button-secondary"
                  onClick={() => {
                    setEditing(null);
                    setCredential("");
                  }}
                >
                  Cancel
                </button>
              )}
            </div>
          </form>
        </section>
      ) : (
        <section className="state-card">
          <WarningCircleIcon size={28} weight="duotone" aria-hidden="true" />
          <h2>Provider management is restricted</h2>
          <p>
            Your role can use configured advisory tools where permitted but cannot change provider
            settings.
          </p>
        </section>
      )}
      {error && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
