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

const axis = { fill: "#8fa4b8", fontSize: 11 };
const tooltip = {
  contentStyle: {
    background: "#0d1927",
    border: "1px solid #31506b",
    borderRadius: "8px",
    color: "#f3f7fb",
    fontSize: "12px",
  },
  labelStyle: { color: "#c7d3df" },
};

export function ActivityChart({ data }: { data: Activity[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} accessibilityLayer>
        <CartesianGrid stroke="#20364b" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="bucket_start"
          tick={axis}
          tickFormatter={(value) => shortTime(String(value))}
        />
        <YAxis allowDecimals={false} tick={axis} />
        <Tooltip
          {...tooltip}
          labelFormatter={(value) => new Date(String(value)).toLocaleString()}
        />
        <Legend />
        <Line
          dataKey="analysis_count"
          name="Analyses"
          stroke="#32dfca"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
        <Line
          dataKey="threat_count"
          name="Threats"
          stroke="#ff9a67"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
        <Line
          dataKey="blocked_count"
          name="Blocked"
          stroke="#ff6e7f"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
        <Line
          dataKey="review_count"
          name="Review"
          stroke="#f6ba59"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
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
        <CartesianGrid stroke="#20364b" strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey={categoryKey} tick={axis} />
        <YAxis allowDecimals={false} tick={axis} />
        <Tooltip {...tooltip} />
        <Bar
          dataKey={valueKey}
          name={label}
          fill="#32dfca"
          radius={[4, 4, 0, 0]}
          isAnimationActive={false}
        />
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
