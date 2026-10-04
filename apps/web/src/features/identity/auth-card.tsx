"use client";

import Image from "next/image";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  ArrowRightIcon,
  CheckCircleIcon,
  LockKeyIcon,
  ShieldCheckIcon,
} from "@phosphor-icons/react";
import { apiRequest, RenzaiApiError } from "@/shared/api/client";

const json = (body: object): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

function errorText(error: unknown): string {
  if (error instanceof RenzaiApiError) return `${error.message} (${error.requestId})`;
  return error instanceof Error ? error.message : "Something went wrong.";
}

export function AuthCard({ onAuthenticated }: { onAuthenticated: () => Promise<void> }) {
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
      return apiRequest(
        `/api/v1/auth/${mode === "login" ? "login" : "register"}`,
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

  const title =
    mode === "login"
      ? "Welcome back"
      : mode === "register"
        ? "Create your account"
        : "Reset your password";
  const submitLabel =
    mode === "login" ? "Sign in" : mode === "register" ? "Create account" : "Request reset";

  return (
    <main className="auth-layout">
      <section className="auth-story" aria-label="About Renzai">
        <div className="auth-story-inner">
          <Image
            src="/brand/renzai-logo.png"
            width={248}
            height={248}
            alt="Renzai"
            className="auth-logo"
            priority
          />
          <div>
            <p className="eyebrow">AI security operations</p>
            <h1>Deterministic protection. Human-centered response.</h1>
            <p className="auth-lead">
              Inspect prompts and model output, enforce policy, and investigate every durable
              security decision from one trusted workspace.
            </p>
          </div>
          <ul className="auth-proof-list">
            <li>
              <ShieldCheckIcon size={20} weight="duotone" aria-hidden="true" />
              <span>
                <strong>Deterministic security</strong>Explainable evidence stays separate from
                optional AI advice.
              </span>
            </li>
            <li>
              <LockKeyIcon size={20} weight="duotone" aria-hidden="true" />
              <span>
                <strong>Tenant isolation</strong>Organization boundaries and role-aware controls are
                preserved.
              </span>
            </li>
            <li>
              <CheckCircleIcon size={20} weight="duotone" aria-hidden="true" />
              <span>
                <strong>Operational clarity</strong>From analysis to incidents without losing the
                original decision.
              </span>
            </li>
          </ul>
        </div>
      </section>

      <section className="auth-form-region">
        <div className="auth-card" aria-labelledby="auth-heading">
          <div className="auth-mobile-brand">
            <Image src="/brand/renzai-logo.png" width={120} height={120} alt="Renzai" />
          </div>
          <p className="eyebrow">Secure workspace</p>
          <h2 id="auth-heading">{title}</h2>
          <p className="muted">
            {mode === "reset"
              ? "Enter your account email and we’ll prepare reset instructions if it exists."
              : "Access your organization’s AI security operations workspace."}
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              setError("");
              setNotice("");
              mutation.mutate(new FormData(event.currentTarget));
            }}
          >
            <label>
              Work email
              <input
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                required
              />
            </label>
            {mode !== "reset" && (
              <label>
                Password
                <input
                  name="password"
                  type="password"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  minLength={12}
                  placeholder="At least 12 characters"
                  required
                />
              </label>
            )}
            {error && (
              <p className="alert alert-error" role="alert">
                {error}
              </p>
            )}
            <button className="button button-primary auth-submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Working…" : submitLabel}
              {!mutation.isPending && <ArrowRightIcon size={18} aria-hidden="true" />}
            </button>
          </form>
          {notice && (
            <p className="alert alert-success" role="status" aria-live="polite">
              {notice}
            </p>
          )}
          <div className="auth-links">
            <button
              className="text-button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                setError("");
                setNotice("");
              }}
            >
              {mode === "login" ? "New to Renzai? Create an account" : "Back to sign in"}
            </button>
            {mode === "login" && (
              <button className="text-button" onClick={() => setMode("reset")}>
                Forgot your password?
              </button>
            )}
          </div>
          <p className="auth-security-note">
            <LockKeyIcon size={15} aria-hidden="true" />
            Credentials are sent only to the configured Renzai API.
          </p>
        </div>
      </section>
    </main>
  );
}
