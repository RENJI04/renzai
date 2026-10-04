"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { Icon } from "@phosphor-icons/react";
import {
  BrainIcon,
  BuildingsIcon,
  ChartLineUpIcon,
  FlaskIcon,
  GearSixIcon,
  KeyIcon,
  ListIcon,
  LockKeyIcon,
  PlugsConnectedIcon,
  ShieldCheckIcon,
  SignOutIcon,
  SirenIcon,
  SquaresFourIcon,
  UserCircleIcon,
  UsersThreeIcon,
  XIcon,
} from "@phosphor-icons/react";

export type WorkspaceOrganization = {
  organization_id: string;
  name: string;
  role: string;
};

type NavItem = {
  href: string;
  label: string;
  description: string;
  icon: Icon;
};

const navigation: Array<{ label: string; items: NavItem[] }> = [
  {
    label: "Monitor",
    items: [
      {
        href: "/dashboard",
        label: "Overview",
        description: "Security posture",
        icon: SquaresFourIcon,
      },
      { href: "/incidents", label: "Incidents", description: "Analyst queue", icon: SirenIcon },
      {
        href: "/analytics",
        label: "Analytics",
        description: "Trends and usage",
        icon: ChartLineUpIcon,
      },
    ],
  },
  {
    label: "Protect",
    items: [
      { href: "/playground", label: "Playground", description: "Test detections", icon: FlaskIcon },
      {
        href: "/policies",
        label: "Policies",
        description: "Decision controls",
        icon: ShieldCheckIcon,
      },
    ],
  },
  {
    label: "Configure",
    items: [
      {
        href: "/applications",
        label: "Applications",
        description: "Environments and keys",
        icon: KeyIcon,
      },
      {
        href: "/providers",
        label: "Gateway providers",
        description: "Model connections",
        icon: PlugsConnectedIcon,
      },
      {
        href: "/ai-intelligence",
        label: "AI Intelligence",
        description: "Advisory providers",
        icon: BrainIcon,
      },
    ],
  },
  {
    label: "Manage",
    items: [
      {
        href: "/organization",
        label: "Organization",
        description: "Members and access",
        icon: UsersThreeIcon,
      },
      {
        href: "/account",
        label: "Account security",
        description: "Identity controls",
        icon: LockKeyIcon,
      },
    ],
  },
];

const pageCopy: Record<string, { eyebrow: string; title: string; summary: string }> = {
  "/": {
    eyebrow: "Security operations",
    title: "Security overview",
    summary: "A real-time view of deterministic analysis, enforcement, and incident posture.",
  },
  "/dashboard": {
    eyebrow: "Security operations",
    title: "Security overview",
    summary: "A real-time view of deterministic analysis, enforcement, and incident posture.",
  },
  "/incidents": {
    eyebrow: "Incident management",
    title: "Analyst workspace",
    summary: "Investigate durable security evidence and clearly separated AI advisory insights.",
  },
  "/analytics": {
    eyebrow: "Observability",
    title: "Security analytics",
    summary: "Explore completed inspection metadata, risk distribution, and provider outcomes.",
  },
  "/playground": {
    eyebrow: "Deterministic security",
    title: "Security playground",
    summary:
      "Test content against the same analysis, risk, and policy pipeline used in production.",
  },
  "/policies": {
    eyebrow: "Policy control",
    title: "Risk policies",
    summary:
      "Manage versioned, scoped decisions without changing the underlying detector evidence.",
  },
  "/applications": {
    eyebrow: "Runtime inventory",
    title: "Applications & environments",
    summary: "Manage tenant-scoped applications, environments, and write-only API credentials.",
  },
  "/providers": {
    eyebrow: "Gateway configuration",
    title: "Gateway providers",
    summary: "Configure encrypted provider connections used by the fail-closed Gateway.",
  },
  "/ai-intelligence": {
    eyebrow: "Advisory intelligence",
    title: "AI Intelligence",
    summary: "Configure optional providers for incident-scoped, clearly labeled advisory analysis.",
  },
  "/organization": {
    eyebrow: "Tenant administration",
    title: "Organization",
    summary: "Manage members and invitations within the active tenant boundary.",
  },
  "/account": {
    eyebrow: "Identity",
    title: "Account security",
    summary: "Maintain verification and password security for your Renzai identity.",
  },
};

export function WorkspaceShell({
  organizations,
  activeOrganization,
  email,
  onOrganizationChange,
  onLogout,
  children,
}: {
  organizations: WorkspaceOrganization[];
  activeOrganization: WorkspaceOrganization;
  email: string;
  onOrganizationChange: (organizationId: string) => void;
  onLogout: () => Promise<void>;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const activeLinkRef = useRef<HTMLAnchorElement>(null);
  const copy = pageCopy[pathname] ?? pageCopy["/dashboard"];

  useEffect(() => {
    activeLinkRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [pathname]);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#workspace-content">
        Skip to content
      </a>
      <aside
        className={`sidebar${mobileOpen ? " sidebar-open" : ""}`}
        aria-label="Primary navigation"
      >
        <div className="sidebar-brand">
          <Image
            src="/brand/renzai-logo.png"
            width={150}
            height={150}
            className="sidebar-logo"
            alt="Renzai"
            priority
          />
          <button
            className="icon-button sidebar-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <XIcon size={20} aria-hidden="true" />
          </button>
        </div>

        <label className="organization-switcher">
          <span>Organization</span>
          <span className="organization-select-wrap">
            <BuildingsIcon size={17} aria-hidden="true" />
            <select
              aria-label="Active organization"
              value={activeOrganization.organization_id}
              onChange={(event) => onOrganizationChange(event.target.value)}
            >
              {organizations.map((organization) => (
                <option key={organization.organization_id} value={organization.organization_id}>
                  {organization.name}
                </option>
              ))}
            </select>
          </span>
        </label>

        <nav className="sidebar-nav">
          {navigation.map((group) => (
            <div className="nav-group" key={group.label}>
              <p>{group.label}</p>
              {group.items.map((item) => {
                const active =
                  pathname === item.href || (pathname === "/" && item.href === "/dashboard");
                const NavIcon = item.icon;
                return (
                  <Link
                    href={item.href}
                    key={item.href}
                    ref={active ? activeLinkRef : undefined}
                    className={active ? "nav-link nav-link-active" : "nav-link"}
                    aria-current={active ? "page" : undefined}
                    onClick={() => setMobileOpen(false)}
                  >
                    <NavIcon size={19} weight={active ? "fill" : "regular"} aria-hidden="true" />
                    <span>
                      <strong>{item.label}</strong>
                      <small>{item.description}</small>
                    </span>
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="security-state">
            <span className="status-dot" />
            <span>
              <strong>Security controls active</strong>
              <small>{activeOrganization.role.replace("_", " ")}</small>
            </span>
          </div>
          <Link href="/account" className="account-link">
            <UserCircleIcon size={28} weight="duotone" aria-hidden="true" />
            <span>
              <strong>{email}</strong>
              <small>Account security</small>
            </span>
          </Link>
          <button className="logout-button" onClick={() => void onLogout()}>
            <SignOutIcon size={18} aria-hidden="true" />
            Sign out
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <button
          className="sidebar-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <div className="workspace-frame">
        <header className="workspace-topbar">
          <button
            className="icon-button mobile-menu"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
          >
            <ListIcon size={22} aria-hidden="true" />
          </button>
          <div className="breadcrumb">
            <span>Renzai</span>
            <span>/</span>
            <strong>{copy.title}</strong>
          </div>
          <div className="topbar-state" title="All requests remain tenant scoped">
            <ShieldCheckIcon size={17} weight="fill" aria-hidden="true" />
            Tenant protected
          </div>
        </header>
        <main id="workspace-content" className="workspace-content" tabIndex={-1}>
          <header className="page-header">
            <div>
              <p className="eyebrow">{copy.eyebrow}</p>
              <h1>{copy.title}</h1>
              <p className="page-summary">{copy.summary}</p>
            </div>
            <div className="page-context">
              <span className="status-dot" />
              <span>
                <small>Active workspace</small>
                <strong>{activeOrganization.name}</strong>
              </span>
            </div>
          </header>
          {children}
        </main>
      </div>
    </div>
  );
}

export function UnsupportedRouteState() {
  return (
    <section className="state-card">
      <GearSixIcon size={28} weight="duotone" aria-hidden="true" />
      <h2>Workspace route unavailable</h2>
      <p>This route is not part of the current Renzai product surface.</p>
      <Link href="/dashboard" className="button button-primary">
        Return to overview
      </Link>
    </section>
  );
}
