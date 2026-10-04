"use client";

import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { CheckCircleIcon, EnvelopeSimpleIcon, KeyIcon, LockKeyIcon } from "@phosphor-icons/react";
import { apiRequest, RenzaiApiError } from "@/shared/api/client";
import type { Session } from "./types";

const json = (body: object): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export function AccountSecurity({ session }: { session: Session }) {
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const mutate = useMutation({
    mutationFn: ({ path, init }: { path: string; init: RequestInit }) =>
      apiRequest(path, init, session.csrf_token),
    onSuccess: () => {
      setError("");
      setNotice("Security setting updated successfully.");
    },
    onError: (failure) => {
      setNotice("");
      setError(
        failure instanceof RenzaiApiError
          ? `${failure.message} (${failure.requestId})`
          : "Security setting could not be updated.",
      );
    },
  });
  const changePassword = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutate.mutate({
      path: "/api/v1/auth/password/change",
      init: json({
        current_password: form.get("current_password"),
        new_password: form.get("new_password"),
      }),
    });
    event.currentTarget.reset();
  };
  return (
    <div className="settings-grid">
      <section className="surface-card settings-card">
        <div className="icon-tile">
          <EnvelopeSimpleIcon size={22} weight="duotone" aria-hidden="true" />
        </div>
        <div>
          <p className="eyebrow">Email identity</p>
          <h2>{session.user.email}</h2>
          <p>Your email anchors this Renzai identity.</p>
        </div>
        <div className="setting-status">
          {session.user.email_verified ? (
            <>
              <CheckCircleIcon size={18} weight="fill" />
              Verified
            </>
          ) : (
            <>
              <LockKeyIcon size={18} />
              Verification pending
            </>
          )}
        </div>
        <button
          className="button button-secondary"
          onClick={() =>
            mutate.mutate({
              path: "/api/v1/auth/email/verification/request",
              init: { method: "POST" },
            })
          }
          disabled={session.user.email_verified || mutate.isPending}
        >
          {session.user.email_verified ? "Email verified" : "Send verification"}
        </button>
      </section>
      <section className="surface-card settings-card">
        <div className="icon-tile">
          <KeyIcon size={22} weight="duotone" aria-hidden="true" />
        </div>
        <div>
          <p className="eyebrow">Credentials</p>
          <h2>Change password</h2>
          <p>Use at least 12 characters and a password unique to Renzai.</p>
        </div>
        <form onSubmit={changePassword}>
          <label>
            Current password
            <input
              aria-label="Current password"
              name="current_password"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          <label>
            New password
            <input
              aria-label="New password"
              name="new_password"
              type="password"
              autoComplete="new-password"
              minLength={12}
              required
            />
          </label>
          <button className="button button-primary" disabled={mutate.isPending}>
            Change password
          </button>
        </form>
      </section>
      {(error || notice) && (
        <p
          className={`alert ${error ? "alert-error" : "alert-success"}`}
          role={error ? "alert" : "status"}
        >
          {error || notice}
        </p>
      )}
    </div>
  );
}
