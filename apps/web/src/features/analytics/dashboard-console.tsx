"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest, RenzaiApiError } from "@/shared/api/client";

const ActivityChart = dynamic(
  () => import("./dashboard-charts").then((item) => item.ActivityChart),
  { ssr: false },
);
const MetricBarChart = dynamic(
  () => import("./dashboard-charts").then((item) => item.MetricBarChart),
  { ssr: false },
);

type Application = { application_id: string; name: string };
type Environment = { environment_id: string; type: string };
type Activity = {
  bucket_start: string;
  analysis_count: number;
  threat_count: number;
  blocked_count: number;
  review_count: number;
};
type Dashboard = {
  filters: { window: string; window_start: string; window_end: string; bucket: string };
  summary: {
    analyses: number;
    gateway_requests: number;
    threats_detected: number;
    blocked: number;
    require_review: number;
    redacted: number;
    critical_analyses: number;
    open_incidents: number;
    threat_rate_numerator: number;
    threat_rate_denominator: number;
    threat_rate_percent: number;
  };
  activity: Activity[];
  risk_distribution: Array<{ severity: string; count: number }>;
  threat_categories: Array<{ category: string; finding_count: number; affected_analyses: number }>;
  top_detectors: Array<{
    detector_id: string;
    detector_version: string;
    finding_count: number;
    affected_analyses: number;
    average_confidence: number;
  }>;
  policy_actions: Array<{ action: string; count: number }>;
  applications: Array<{
    application_id: string;
    application_name: string;
    analysis_count: number;
    threat_count: number;
    critical_count: number;
    blocked_count: number;
    incident_count: number;
  }>;
  environments: Array<{
    environment_id: string;
    environment_type: string;
    analysis_count: number;
    threat_count: number;
    blocked_count: number;
    incident_count: number;
  }>;
  providers: Array<{
    provider_id: string;
    provider_name: string;
    configured_model: string;
    request_count: number;
    completed: number;
    provider_timeout: number;
    provider_error: number;
    configuration_error: number;
    output_block: number;
    output_review: number;
    output_inspection_failure: number;
    average_latency_ms: number;
  }>;
  incidents: {
    statuses: Array<{ status: string; count: number }>;
    critical_open: number;
    unassigned_open: number;
  };
  recent_incidents: Array<{
    incident_id: string;
    status: string;
    severity: string;
    category: string | null;
    action: string | null;
    created_at: string;
  }>;
  query_duration_ms: number;
};

const windows = ["24h", "7d", "30d", "90d"] as const;

export function DashboardConsole({ organizationId }: { organizationId: string }) {
  const [window, setWindow] = useState<(typeof windows)[number]>("24h");
  const [applicationId, setApplicationId] = useState("");
  const [environmentId, setEnvironmentId] = useState("");
  const [source, setSource] = useState("");
  const applications = useQuery({
    queryKey: ["applications", organizationId],
    queryFn: () =>
      apiRequest<{ items: Application[] }>(`/api/v1/organizations/${organizationId}/applications`),
  });
  const environments = useQuery({
    queryKey: ["environments", organizationId, applicationId],
    queryFn: () =>
      apiRequest<{ items: Environment[] }>(
        `/api/v1/organizations/${organizationId}/applications/${applicationId}/environments`,
      ),
    enabled: Boolean(applicationId),
  });
  const params = new URLSearchParams({ window });
  if (applicationId) params.set("application_id", applicationId);
  if (environmentId) params.set("environment_id", environmentId);
  if (source) params.set("source", source);
  const dashboard = useQuery({
    queryKey: ["analytics-dashboard", organizationId, window, applicationId, environmentId, source],
    queryFn: () =>
      apiRequest<Dashboard>(
        `/api/v1/organizations/${organizationId}/analytics/dashboard?${params.toString()}`,
      ),
    retry: false,
  });

  return (
    <section className="panel dashboard" aria-labelledby="dashboard-heading">
      <header className="dashboard-header">
        <div>
          <p className="eyebrow">OPERATIONS</p>
          <h2 id="dashboard-heading">Security dashboard</h2>
          <p className="muted">Completed inspection and Gateway outcome metadata in UTC.</p>
        </div>
        <div className="dashboard-filters" aria-label="Dashboard filters">
          <label>
            Window
            <select
              aria-label="Dashboard window"
              value={window}
              onChange={(event) => setWindow(event.target.value as (typeof windows)[number])}
            >
              {windows.map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          </label>
          <label>
            Application
            <select
              aria-label="Dashboard application"
              value={applicationId}
              onChange={(event) => {
                setApplicationId(event.target.value);
                setEnvironmentId("");
              }}
            >
              <option value="">All applications</option>
              {applications.data?.items.map((application) => (
                <option key={application.application_id} value={application.application_id}>
                  {application.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Environment
            <select
              aria-label="Dashboard environment"
              value={environmentId}
              disabled={!applicationId}
              onChange={(event) => setEnvironmentId(event.target.value)}
            >
              <option value="">All environments</option>
              {environments.data?.items.map((environment) => (
                <option key={environment.environment_id} value={environment.environment_id}>
                  {environment.type}
                </option>
              ))}
            </select>
          </label>
          <label>
            Source
            <select
              aria-label="Dashboard source"
              value={source}
              onChange={(event) => setSource(event.target.value)}
            >
              <option value="">All sources</option>
              <option value="analyze">Analyze API</option>
              <option value="playground">Playground</option>
              <option value="gateway">Gateway</option>
            </select>
          </label>
        </div>
      </header>
      {dashboard.isPending ? <DashboardSkeleton /> : null}
      {dashboard.isError ? <DashboardError error={dashboard.error} /> : null}
      {dashboard.data ? <DashboardBody data={dashboard.data} /> : null}
    </section>
  );
}

function DashboardBody({ data }: { data: Dashboard }) {
  const empty = data.summary.analyses === 0 && data.summary.gateway_requests === 0;
  return (
    <div aria-live="polite">
      <div className="kpi-grid">
        <Kpi label="Analyses" value={data.summary.analyses} />
        <Kpi label="Threats detected" value={data.summary.threats_detected} />
        <Kpi label="Blocked" value={data.summary.blocked} />
        <Kpi label="Critical Analyses" value={data.summary.critical_analyses} />
        <Kpi label="Open incidents" value={data.summary.open_incidents} />
        <Kpi label="Threat rate" value={`${data.summary.threat_rate_percent}%`} />
        <Kpi label="Gateway requests" value={data.summary.gateway_requests} />
      </div>
      {empty ? <p className="empty dashboard-empty">No security activity in this period</p> : null}
      <div className="dashboard-grid">
        <DashboardPanel title="Activity" wide>
          <div role="img" aria-label="Analyses, threats, blocked, and review activity over time">
            <ActivityChart data={data.activity} />
          </div>
          <AccessibleMetricTable
            caption="Activity values"
            rows={data.activity}
            labelKey="bucket_start"
            valueKeys={["analysis_count", "threat_count", "blocked_count", "review_count"]}
          />
        </DashboardPanel>
        <DashboardPanel title="Final risk distribution">
          <MetricBarChart
            data={data.risk_distribution}
            categoryKey="severity"
            valueKey="count"
            label="Analyses"
          />
          <AccessibleMetricTable
            caption="Risk distribution values"
            rows={data.risk_distribution}
            labelKey="severity"
            valueKeys={["count"]}
          />
        </DashboardPanel>
        <DashboardPanel title="Threat categories">
          <MetricBarChart
            data={data.threat_categories}
            categoryKey="category"
            valueKey="finding_count"
            label="Findings"
          />
          <AccessibleMetricTable
            caption="Threat category values"
            rows={data.threat_categories}
            labelKey="category"
            valueKeys={["finding_count", "affected_analyses"]}
          />
        </DashboardPanel>
        <DashboardPanel title="Policy actions">
          <MetricBarChart
            data={data.policy_actions}
            categoryKey="action"
            valueKey="count"
            label="Decisions"
          />
          <AccessibleMetricTable
            caption="Policy action values"
            rows={data.policy_actions}
            labelKey="action"
            valueKeys={["count"]}
          />
        </DashboardPanel>
        <DashboardPanel title="Incident status">
          <ul className="metric-list">
            {data.incidents.statuses.map((item) => (
              <li key={item.status}>
                <span>{humanize(item.status)}</span>
                <strong>{item.count}</strong>
              </li>
            ))}
            <li>
              <span>Critical open</span>
              <strong>{data.incidents.critical_open}</strong>
            </li>
            <li>
              <span>Unassigned open</span>
              <strong>{data.incidents.unassigned_open}</strong>
            </li>
          </ul>
          <a href="#incident-queue">Open Incident Queue</a>
        </DashboardPanel>
        <DashboardPanel title="Recent incidents">
          {data.recent_incidents.length === 0 ? (
            <p className="muted">No incidents created in this period.</p>
          ) : (
            <ul className="metric-list recent-incidents">
              {data.recent_incidents.map((incident) => (
                <li key={incident.incident_id}>
                  <span>
                    <strong>{humanize(incident.severity)}</strong>
                    {incident.category ? ` · ${humanize(incident.category)}` : ""}
                    {incident.action ? ` · ${humanize(incident.action)}` : ""}
                  </span>
                  <small>
                    {humanize(incident.status)} · {new Date(incident.created_at).toLocaleString()}
                  </small>
                </li>
              ))}
            </ul>
          )}
        </DashboardPanel>
        <DashboardPanel title="Provider usage" wide>
          {data.providers.length === 0 ? (
            <p className="muted">No Gateway provider calls.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Provider / model</th>
                    <th>Requests</th>
                    <th>Completed</th>
                    <th>Timeouts</th>
                    <th>Errors</th>
                    <th>Output enforcement</th>
                    <th>Avg latency</th>
                  </tr>
                </thead>
                <tbody>
                  {data.providers.map((provider) => (
                    <tr key={`${provider.provider_id}-${provider.configured_model}`}>
                      <td>
                        {provider.provider_name}
                        <small>{provider.configured_model}</small>
                      </td>
                      <td>{provider.request_count}</td>
                      <td>{provider.completed}</td>
                      <td>{provider.provider_timeout}</td>
                      <td>{provider.provider_error + provider.configuration_error}</td>
                      <td>
                        {provider.output_block +
                          provider.output_review +
                          provider.output_inspection_failure}
                      </td>
                      <td>{provider.average_latency_ms} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DashboardPanel>
      </div>
      <p className="dashboard-footnote">
        Inclusive window: {new Date(data.filters.window_start).toLocaleString()} –{" "}
        {new Date(data.filters.window_end).toLocaleString()} · query {data.query_duration_ms} ms
      </p>
    </div>
  );
}

function DashboardPanel({
  title,
  wide = false,
  children,
}: {
  title: string;
  wide?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section className={`dashboard-card${wide ? " dashboard-card-wide" : ""}`}>
      <h3>{title}</h3>
      {children}
    </section>
  );
}
function Kpi({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="kpi">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
function AccessibleMetricTable({
  caption,
  rows,
  labelKey,
  valueKeys,
}: {
  caption: string;
  rows: Array<Record<string, string | number>>;
  labelKey: string;
  valueKeys: string[];
}) {
  return (
    <details className="chart-values">
      <summary>View values</summary>
      <div className="table-scroll">
        <table>
          <caption>{caption}</caption>
          <thead>
            <tr>
              <th>{humanize(labelKey)}</th>
              {valueKeys.map((key) => (
                <th key={key}>{humanize(key)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row[labelKey]}-${index}`}>
                <td>{String(row[labelKey])}</td>
                {valueKeys.map((key) => (
                  <td key={key}>{row[key]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
function DashboardSkeleton() {
  return (
    <div className="dashboard-skeleton" role="status">
      <span>Loading dashboard…</span>
      <div />
      <div />
      <div />
    </div>
  );
}
function DashboardError({ error }: { error: unknown }) {
  const message =
    error instanceof RenzaiApiError
      ? `${error.message} (${error.requestId})`
      : "Dashboard data could not be loaded.";
  return (
    <p className="error" role="alert">
      {message}
    </p>
  );
}
function humanize(value: string): string {
  return value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}
