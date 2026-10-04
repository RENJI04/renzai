"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, RenzaiApiError } from "@/shared/api/client";

type Provider = {
  provider_id: string;
  kind: "openai_compatible_remote" | "openai_compatible_local";
  name: string;
  base_url: string;
  model: string;
  credential_present: boolean;
  supports_seed: boolean;
  max_tokens: number;
  status: "active" | "disabled";
  last_validation_status: "never" | "success" | "failure";
};

const json = (body: object, method = "POST"): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function message(error: unknown): string {
  if (error instanceof RenzaiApiError) return `${error.message} (${error.requestId})`;
  return error instanceof Error ? error.message : "Something went wrong.";
}

export function ProviderManager({
  organizationId,
  applicationId,
  environmentId,
  role,
  csrfToken,
}: {
  organizationId: string;
  applicationId: string;
  environmentId: string;
  role: string;
  csrfToken: string;
}) {
  const queryClient = useQueryClient();
  const canManage = role === "owner" || role === "admin";
  const path = `/api/v1/organizations/${organizationId}/applications/${applicationId}/environments/${environmentId}/providers`;
  const [editing, setEditing] = useState<Provider | null>(null);
  const [kind, setKind] = useState<Provider["kind"]>("openai_compatible_remote");
  const [credential, setCredential] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const providers = useQuery({
    queryKey: ["providers", organizationId, applicationId, environmentId],
    queryFn: () => apiRequest<{ items: Provider[] }>(path),
  });
  const action = useMutation({
    mutationFn: ({ suffix }: { suffix: string }) =>
      apiRequest(`${path}/${suffix}`, { method: "POST" }, csrfToken),
    onSuccess: async () => {
      setError("");
      await queryClient.invalidateQueries({
        queryKey: ["providers", organizationId, applicationId, environmentId],
      });
    },
    onError: (failure) => setError(message(failure)),
  });

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const body: Record<string, unknown> = {
      kind: form.get("kind") as string,
      name: form.get("name") as string,
      base_url: form.get("base_url") as string,
      model: form.get("model") as string,
      supports_seed: form.get("supports_seed") === "on",
      max_tokens: Number(form.get("max_tokens")),
    };
    if (credential) body.credential = credential;
    try {
      await apiRequest(
        editing ? `${path}/${editing.provider_id}` : path,
        json(body, editing ? "PATCH" : "POST"),
        csrfToken,
      );
      setCredential("");
      setEditing(null);
      setKind("openai_compatible_remote");
      event.currentTarget.reset();
      await queryClient.invalidateQueries({
        queryKey: ["providers", organizationId, applicationId, environmentId],
      });
    } catch (failure) {
      setError(message(failure));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="surface-card" aria-labelledby="providers-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Encrypted connections</p>
          <h2 id="providers-heading">Provider configurations</h2>
          <p>Credentials are encrypted at rest and are never displayed after submission.</p>
        </div>
      </div>
      {providers.isPending && (
        <p role="status" aria-live="polite">
          Loading provider configurations…
        </p>
      )}
      {providers.isError && (
        <p className="error" role="alert">
          {message(providers.error)}
        </p>
      )}
      {!providers.isPending && !providers.isError && providers.data?.items.length === 0 && (
        <div className="empty-state">
          <h3>No Gateway provider configured</h3>
          <p>Add an OpenAI-compatible endpoint for this application environment.</p>
        </div>
      )}
      <div className="provider-list">
        {providers.data?.items.map((provider) => (
          <article key={provider.provider_id}>
            <div>
              <strong>{provider.name}</strong>
              <p>
                {provider.kind} · {provider.model} · {provider.status} · validation{" "}
                {provider.last_validation_status}
              </p>
              <code>{provider.base_url}</code>
              <p>Credential: {provider.credential_present ? "configured" : "not configured"}</p>
            </div>
            {canManage && (
              <span className="actions">
                <button
                  type="button"
                  onClick={() => {
                    setEditing(provider);
                    setKind(provider.kind);
                    setCredential("");
                  }}
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() =>
                    action.mutate({
                      suffix: `${provider.provider_id}/${
                        provider.status === "active" ? "disable" : "enable"
                      }`,
                    })
                  }
                >
                  {provider.status === "active" ? "Disable" : "Enable"}
                </button>
                <button
                  type="button"
                  onClick={() => action.mutate({ suffix: `${provider.provider_id}/validate` })}
                >
                  Test provider
                </button>
              </span>
            )}
          </article>
        ))}
      </div>
      {canManage && (
        <form className="provider-form" onSubmit={save} key={editing?.provider_id ?? "create"}>
          <h3>{editing ? "Update provider" : "Create provider"}</h3>
          <div className="resource-grid">
            <label>
              Kind
              <select
                name="kind"
                value={kind}
                onChange={(event) => setKind(event.target.value as Provider["kind"])}
              >
                <option value="openai_compatible_remote">Remote OpenAI-compatible</option>
                <option value="openai_compatible_local">Explicit local provider</option>
              </select>
            </label>
            <label>
              Name
              <input name="name" defaultValue={editing?.name ?? ""} required />
            </label>
            <label>
              Base URL
              <input
                name="base_url"
                type="url"
                defaultValue={editing?.base_url ?? ""}
                placeholder="https://provider.example/v1"
                required
              />
            </label>
            <label>
              Model
              <input name="model" defaultValue={editing?.model ?? ""} required />
            </label>
            <label>
              Credential {editing && "(leave blank to keep current)"}
              <input
                aria-label="Provider credential"
                type="password"
                autoComplete="new-password"
                value={credential}
                onChange={(event) => setCredential(event.target.value)}
                required={!editing && kind === "openai_compatible_remote"}
              />
            </label>
            <label>
              Maximum tokens
              <input
                name="max_tokens"
                type="number"
                min="1"
                max="4096"
                defaultValue={editing?.max_tokens ?? 4096}
                required
              />
            </label>
          </div>
          <label className="checkbox-label">
            <input
              name="supports_seed"
              type="checkbox"
              defaultChecked={editing?.supports_seed ?? false}
            />
            Provider supports the seed parameter
          </label>
          <span className="actions">
            <button className="primary" disabled={saving}>
              {saving ? "Saving…" : editing ? "Save provider" : "Create provider"}
            </button>
            {editing && (
              <button
                type="button"
                onClick={() => {
                  setEditing(null);
                  setKind("openai_compatible_remote");
                  setCredential("");
                }}
              >
                Cancel
              </button>
            )}
          </span>
        </form>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
