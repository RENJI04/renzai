"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheckIcon } from "@phosphor-icons/react";
import { DashboardConsole } from "@/features/analytics/dashboard-console";
import { AIProviderConsole } from "@/features/incidents/ai-provider-console";
import { IncidentConsole } from "@/features/incidents/incident-console";
import { SecurityConsole } from "@/features/security/security-console";
import { apiRequest } from "@/shared/api/client";
import { UnsupportedRouteState, WorkspaceShell } from "@/shared/ui/workspace-shell";
import { AccountSecurity } from "./account-security";
import { AuthCard } from "./auth-card";
import { OrganizationConsole, OrganizationOnboarding } from "./organization-console";
import type { Organization, Session } from "./types";

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
    queryClient.removeQueries();
  };

  if (sessionQuery.isPending) {
    return (
      <main className="boot-screen">
        <div className="boot-mark">
          <ShieldCheckIcon size={30} weight="duotone" aria-hidden="true" />
        </div>
        <p role="status" aria-live="polite">
          Loading your workspace…
        </p>
      </main>
    );
  }
  if (!sessionQuery.data) return <AuthCard onAuthenticated={refresh} />;
  return <Workspace session={sessionQuery.data} onLoggedOut={clearSession} />;
}

function Workspace({ session, onLoggedOut }: { session: Session; onLoggedOut: () => void }) {
  const pathname = usePathname();
  const organizations = useQuery({
    queryKey: ["organizations"],
    queryFn: () => apiRequest<{ items: Organization[] }>("/api/v1/organizations"),
  });
  const [activeId, setActiveId] = useState<string | null>(null);
  const active =
    organizations.data?.items.find((item) => item.organization_id === activeId) ??
    organizations.data?.items[0];

  if (organizations.isPending) {
    return (
      <main className="boot-screen">
        <span className="spinner" />
        <p role="status">Loading organizations…</p>
      </main>
    );
  }
  if (!active) return <OrganizationOnboarding session={session} />;

  const logout = async () => {
    await apiRequest("/api/v1/auth/logout", { method: "POST" }, session.csrf_token);
    onLoggedOut();
  };

  return (
    <WorkspaceShell
      organizations={organizations.data?.items ?? []}
      activeOrganization={active}
      email={session.user.email}
      onOrganizationChange={setActiveId}
      onLogout={logout}
    >
      <WorkspaceRoute pathname={pathname} active={active} session={session} />
    </WorkspaceShell>
  );
}

function WorkspaceRoute({
  pathname,
  active,
  session,
}: {
  pathname: string;
  active: Organization;
  session: Session;
}) {
  const common = {
    organizationId: active.organization_id,
    role: active.role,
    csrfToken: session.csrf_token,
  };
  switch (pathname) {
    case "/":
    case "/dashboard":
      return <DashboardConsole organizationId={active.organization_id} mode="overview" />;
    case "/analytics":
      return <DashboardConsole organizationId={active.organization_id} mode="analytics" />;
    case "/incidents":
      return <IncidentConsole {...common} />;
    case "/playground":
      return <SecurityConsole {...common} view="playground" />;
    case "/policies":
      return <SecurityConsole {...common} view="policies" />;
    case "/applications":
      return <SecurityConsole {...common} view="applications" />;
    case "/providers":
      return <SecurityConsole {...common} view="providers" />;
    case "/ai-intelligence":
      return <AIProviderConsole {...common} />;
    case "/organization":
      return <OrganizationConsole active={active} session={session} />;
    case "/account":
      return <AccountSecurity session={session} />;
    default:
      return <UnsupportedRouteState />;
  }
}
