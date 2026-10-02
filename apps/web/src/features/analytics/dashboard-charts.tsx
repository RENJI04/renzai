"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Activity = {
  bucket_start: string;
  analysis_count: number;
  threat_count: number;
  blocked_count: number;
  review_count: number;
};
type Metric = Record<string, string | number>;

const axis = { fill: "#9db0c4", fontSize: 12 };

export function ActivityChart({ data }: { data: Activity[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} accessibilityLayer>
        <CartesianGrid stroke="#263a50" strokeDasharray="3 3" />
        <XAxis
          dataKey="bucket_start"
          tick={axis}
          tickFormatter={(value) => shortTime(String(value))}
        />
        <YAxis allowDecimals={false} tick={axis} />
        <Tooltip labelFormatter={(value) => new Date(String(value)).toLocaleString()} />
        <Legend />
        <Line dataKey="analysis_count" name="Analyses" stroke="#51dfb6" dot={false} />
        <Line dataKey="threat_count" name="Threats" stroke="#ffad66" dot={false} />
        <Line dataKey="blocked_count" name="Blocked" stroke="#ff7a7a" dot={false} />
        <Line dataKey="review_count" name="Review" stroke="#f2d56b" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function MetricBarChart({
  data,
  categoryKey,
  valueKey,
  label,
}: {
  data: Metric[];
  categoryKey: string;
  valueKey: string;
  label: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} accessibilityLayer>
        <CartesianGrid stroke="#263a50" strokeDasharray="3 3" />
        <XAxis dataKey={categoryKey} tick={axis} />
        <YAxis allowDecimals={false} tick={axis} />
        <Tooltip />
        <Bar dataKey={valueKey} name={label} fill="#51dfb6" />
      </BarChart>
    </ResponsiveContainer>
  );
}

function shortTime(value: string): string {
  const date = new Date(value);
  return date.getUTCHours() === 0
    ? date.toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" })
    : `${String(date.getUTCHours()).padStart(2, "0")}:00`;
}
