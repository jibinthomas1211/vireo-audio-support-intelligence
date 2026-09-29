import {
  BarChart, Bar, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Area, AreaChart,
  PieChart, Pie, Cell,
} from "recharts";
import { api } from "../api";
import {
  useApi,
} from "./shared";
import { formatINR, formatNum, formatPct, CHART_COLORS } from "./formatters";
import { Loading, ErrorDisplay } from "./ui";

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "#ffffff",
        border: "1px solid #dbe4ef",
        borderRadius: "8px",
        padding: "10px 14px",
        fontSize: "0.8rem",
      }}
    >
      <div style={{ color: "#65728a", marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, fontWeight: 600 }}>
          {p.name}: {typeof p.value === "number" && p.value > 1000 ? formatNum(p.value) : p.value}
        </div>
      ))}
    </div>
  );
};

export default function OverviewPanel() {
  const { data: overview, loading: loadingO, error: errorO } = useApi(api.getOverview);
  const { data: trends, loading: loadingT } = useApi(api.getTrends);
  const { data: insights } = useApi(api.getInsights);

  if (loadingO) return <Loading />;
  if (errorO) return <ErrorDisplay message={errorO} />;
  if (!overview) return null;

  const channelData = overview.breach_by_channel
    ? Object.entries(overview.breach_by_channel).map(([ch, d]) => ({
        name: ch.charAt(0).toUpperCase() + ch.slice(1),
        total: d.total,
        breached: d.breached,
        rate: d.rate,
      }))
    : [];

  const statusData = overview.status_breakdown
    ? Object.entries(overview.status_breakdown).map(([s, cnt]) => ({
        name: s.charAt(0).toUpperCase() + s.slice(1),
        value: cnt,
      }))
    : [];

  return (
    <div className="fade-in">
      {/* KPI Row */}
      <div className="kpi-row">
        <div className="kpi-card">
          <div className="kpi-icon teal">📋</div>
          <div className="kpi-label">Unique Tickets</div>
          <div className="kpi-value accent">{formatNum(overview.unique_tickets)}</div>
          <div className="kpi-sub">{overview.duplicate_tickets} duplicates removed</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon amber">🔄</div>
          <div className="kpi-label">Repeat Contact Rate</div>
          <div className="kpi-value warn">{formatPct(overview.repeat_contact_rate)}</div>
          <div className="kpi-sub">{formatNum(overview.repeat_contacts)} repeat contacts · {formatINR(overview.repeat_contact_cost)} cost</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon red">⏱</div>
          <div className="kpi-label">SLA Breaches</div>
          <div className="kpi-value danger">{formatNum(overview.sla_breaches)}</div>
          <div className="kpi-sub">{formatPct(overview.sla_breach_rate)} breach rate · {formatINR(overview.sla_breach_cost)} in credits</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon green">⭐</div>
          <div className="kpi-label">Avg CSAT</div>
          <div className="kpi-value good">{overview.avg_csat}/5</div>
          <div className="kpi-sub">Excluding no-response (0 / blank)</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon blue">💰</div>
          <div className="kpi-label">Total Refunds</div>
          <div className="kpi-value">{formatINR(overview.total_refunds)}</div>
          <div className="kpi-sub">{formatNum(overview.replacements)} replacements issued</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon rose">⚠️</div>
          <div className="kpi-label">Policy Violations</div>
          <div className="kpi-value danger">{overview.refund_and_replacement_violations}</div>
          <div className="kpi-sub">Refund + replacement on same ticket</div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="chart-grid">
        {/* Volume Trend */}
        <div className="section-card">
          <div className="section-header">
            <h2>📈 Weekly Ticket Volume</h2>
          </div>
          <div className="section-body">
            {loadingT ? (
              <Loading text="Loading trend data..." />
            ) : (
              <div className="chart-container">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trends}>
                    <defs>
                      <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2864e8" stopOpacity={0.22} />
                        <stop offset="95%" stopColor="#2864e8" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis
                      dataKey="week"
                      tick={{ fill: "#5c6478", fontSize: 10 }}
                      axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                      interval={7}
                    />
                    <YAxis
                      tick={{ fill: "#5c6478", fontSize: 11 }}
                      axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="total"
                      stroke="#2864e8"
                      strokeWidth={2}
                      fill="url(#colorTotal)"
                      name="Tickets"
                    />
                    <Line
                      type="monotone"
                      dataKey="breaches"
                      stroke="#ef4444"
                      strokeWidth={1.5}
                      dot={false}
                      name="SLA Breaches"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        {/* Channel Breakdown */}
        <div className="section-card">
          <div className="section-header">
            <h2>📊 SLA Performance by Channel</h2>
          </div>
          <div className="section-body">
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={channelData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: "#8a92a8", fontSize: 12 }}
                    axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                  />
                  <YAxis
                    tick={{ fill: "#5c6478", fontSize: 11 }}
                    axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="total" fill="#2864e8" name="Total Tickets" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="breached" fill="#ef4444" name="SLA Breaches" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Status Distribution */}
        <div className="section-card">
          <div className="section-header">
            <h2>📋 Ticket Status</h2>
          </div>
          <div className="section-body">
            <div className="chart-container" style={{ display: "flex", alignItems: "center", gap: "2rem" }}>
              <ResponsiveContainer width="50%" height="100%">
                <PieChart>
                  <Pie
                    data={statusData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    dataKey="value"
                    stroke="none"
                  >
                    {statusData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {statusData.map((s, i) => (
                  <div key={s.name} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: 3,
                        background: CHART_COLORS[i % CHART_COLORS.length],
                      }}
                    />
                    <span style={{ fontSize: "0.82rem", color: "#8a92a8" }}>{s.name}</span>
                    <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "#f0f2f8", marginLeft: "auto" }}>
                      {formatNum(s.value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Category Insights */}
        {insights?.category_insights && (
          <div className="section-card">
            <div className="section-header">
              <h2>🏷️ Category Breakdown</h2>
            </div>
            <div className="section-body">
              <div className="cat-bar-container">
                {insights.category_insights.map((cat, i) => {
                  const maxCount = insights.category_insights[0]?.total || 1;
                  const pct = (cat.total / maxCount) * 100;
                  return (
                    <div className="cat-bar-item" key={cat.category}>
                      <div className="cat-bar-label">{cat.category}</div>
                      <div className="cat-bar-track">
                        <div
                          className="cat-bar-fill"
                          style={{
                            width: `${pct}%`,
                            background: CHART_COLORS[i % CHART_COLORS.length],
                            opacity: 0.8,
                          }}
                        />
                      </div>
                      <div className="cat-bar-value">{formatNum(cat.total)}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
