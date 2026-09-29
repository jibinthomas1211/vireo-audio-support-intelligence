import {
  Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Area, AreaChart, Cell,
} from "recharts";
import { api } from "../api";
import {
  useApi,
} from "./shared";
import { formatINR, formatNum, formatPct } from "./formatters";
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
      <div style={{ color: "#8a92a8", marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, fontWeight: 600 }}>
          {p.name}: {p.value}
          {p.name.includes("Rate") ? "%" : ""}
        </div>
      ))}
    </div>
  );
};

export default function InsightsPanel() {
  const { data: insights, loading, error } = useApi(api.getInsights);

  if (loading) return <Loading text="Loading insights..." />;
  if (error) return <ErrorDisplay message={error} />;
  if (!insights) return null;

  const repeatTrend = insights.repeat_contact_trend || [];
  const slaTrend = insights.sla_breach_trend || [];
  const anomalies = insights.refund_replacement_anomalies || [];
  const transferTeams = insights.transfer_by_team || [];
  const csatDist = insights.csat_distribution || [];
  const catInsights = insights.category_insights || [];

  // Compute summary metrics
  const totalRepeats = repeatTrend.reduce((s, r) => s + r.repeat_count, 0);
  const avgRepeatRate =
    repeatTrend.length > 0
      ? (repeatTrend.reduce((s, r) => s + r.rate, 0) / repeatTrend.length).toFixed(1)
      : 0;
  const totalBreaches = slaTrend.reduce((s, r) => s + r.breaches, 0);
  const totalTransferCost = transferTeams.reduce((s, t) => s + t.transfer_cost, 0);

  return (
    <div className="fade-in">
      {/* Summary KPIs */}
      <div className="kpi-row">
        <div className="kpi-card">
          <div className="kpi-icon amber">🔄</div>
          <div className="kpi-label">Total Repeat Contacts</div>
          <div className="kpi-value warn">{formatNum(totalRepeats)}</div>
          <div className="kpi-sub">Avg {avgRepeatRate}% rate · {formatINR(totalRepeats * 290)} cost</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon red">⏱</div>
          <div className="kpi-label">Total SLA Breaches</div>
          <div className="kpi-value danger">{formatNum(totalBreaches)}</div>
          <div className="kpi-sub">{formatINR(totalBreaches * 350)} in auto-credits</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon blue">↔️</div>
          <div className="kpi-label">Transfer Costs</div>
          <div className="kpi-value">{formatINR(totalTransferCost)}</div>
          <div className="kpi-sub">₹305 per inter-team transfer</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon rose">⚠️</div>
          <div className="kpi-label">Policy Violations</div>
          <div className="kpi-value danger">{anomalies.length}</div>
          <div className="kpi-sub">Refund + replacement on same ticket</div>
        </div>
      </div>

      <div className="chart-grid">
        {/* Repeat Contact Trend */}
        <div className="section-card">
          <div className="section-header">
            <h2>🔄 Repeat Contact Rate Trend</h2>
            <span className="badge amber">Target: &lt;20%</span>
          </div>
          <div className="section-body">
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={repeatTrend}>
                  <defs>
                    <linearGradient id="repeatGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f6c455" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#f6c455" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    dataKey="week"
                    tick={{ fill: "#5c6478", fontSize: 10 }}
                    interval={7}
                    axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                  />
                  <YAxis
                    tick={{ fill: "#5c6478", fontSize: 11 }}
                    axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                    unit="%"
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="rate"
                    stroke="#f6c455"
                    strokeWidth={2}
                    fill="url(#repeatGrad)"
                    name="Repeat Rate"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* SLA Breach Trend */}
        <div className="section-card">
          <div className="section-header">
            <h2>⏱ SLA Breach Trend</h2>
            <span className="badge red">₹350 per breach</span>
          </div>
          <div className="section-body">
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={slaTrend}>
                  <defs>
                    <linearGradient id="slaGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    dataKey="week"
                    tick={{ fill: "#5c6478", fontSize: 10 }}
                    interval={7}
                    axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                  />
                  <YAxis
                    tick={{ fill: "#5c6478", fontSize: 11 }}
                    axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="breaches"
                    stroke="#ef4444"
                    strokeWidth={2}
                    fill="url(#slaGrad)"
                    name="Breaches"
                  />
                  <Line
                    type="monotone"
                    dataKey="total"
                    stroke="#2864e8"
                    strokeWidth={1}
                    dot={false}
                    name="Total Tickets"
                    strokeDasharray="4 4"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* CSAT Distribution */}
        <div className="section-card">
          <div className="section-header">
            <h2>⭐ CSAT Distribution</h2>
            <span className="badge green">Excludes 0/blank (no response)</span>
          </div>
          <div className="section-body">
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={csatDist}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    dataKey="score"
                    tick={{ fill: "#8a92a8", fontSize: 12 }}
                    axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                  />
                  <YAxis
                    tick={{ fill: "#5c6478", fontSize: 11 }}
                    axisLine={{ stroke: "rgba(255,255,255,0.06)" }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" name="Responses" radius={[4, 4, 0, 0]}>
                    {csatDist.map((entry, i) => {
                      const color =
                        entry.score >= 4 ? "#34d399" : entry.score >= 3 ? "#f6c455" : "#ef4444";
                      return <Cell key={i} fill={color} />;
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Transfer Cost by Team */}
        <div className="section-card">
          <div className="section-header">
            <h2>↔️ Inter-Team Transfer Costs</h2>
            <span className="badge blue">₹305 per transfer</span>
          </div>
          <div className="section-body">
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Team</th>
                    <th>Tickets w/ Transfers</th>
                    <th>Total Transfers</th>
                    <th>Avg Transfers/Ticket</th>
                    <th>Transfer Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {transferTeams.map((t) => (
                    <tr key={t.team}>
                      <td style={{ fontWeight: 600, color: "var(--text-primary)" }}>{t.team}</td>
                      <td>{formatNum(t.tickets_with_transfers)}</td>
                      <td style={{ fontWeight: 600 }}>{formatNum(t.total_transfers)}</td>
                      <td>{t.avg_transfers}</td>
                      <td style={{ fontWeight: 600, color: "var(--accent-amber)" }}>
                        {formatINR(t.transfer_cost)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Refund + Replacement Anomalies */}
        {anomalies.length > 0 && (
          <div className="section-card" style={{ gridColumn: "1 / -1" }}>
            <div className="section-header">
              <h2>⚠️ Policy Violations — Refund + Replacement on Same Ticket</h2>
              <span className="badge red">Requires escalation per §5</span>
            </div>
            <div className="section-body">
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Ticket ID</th>
                      <th>Date</th>
                      <th>Customer</th>
                      <th>Product</th>
                      <th>Refund Amount</th>
                      <th>Reason Code</th>
                      <th>Agent</th>
                    </tr>
                  </thead>
                  <tbody>
                    {anomalies.map((a) => (
                      <tr key={a.ticket_id}>
                        <td style={{ fontWeight: 600, color: "var(--accent-red)" }}>{a.ticket_id}</td>
                        <td>{a.created_at}</td>
                        <td>{a.customer_id}</td>
                        <td>{a.product_name || a.product_sku}</td>
                        <td style={{ fontWeight: 600 }}>{formatINR(a.refund_amount)}</td>
                        <td><span className="badge amber">{a.reason_code}</span></td>
                        <td>{a.agent_name} ({a.agent_id})</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Category Performance */}
        <div className="section-card" style={{ gridColumn: "1 / -1" }}>
          <div className="section-header">
            <h2>🏷️ Category Performance Deep-Dive</h2>
          </div>
          <div className="section-body">
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Total Tickets</th>
                    <th>Avg CSAT</th>
                    <th>SLA Breaches</th>
                    <th>Breach Rate</th>
                    <th>Avg Response (min)</th>
                    <th>Refunds</th>
                    <th>Total Refunded</th>
                  </tr>
                </thead>
                <tbody>
                  {catInsights.map((c) => (
                    <tr key={c.category}>
                      <td style={{ fontWeight: 600, color: "var(--text-primary)" }}>{c.category}</td>
                      <td>{formatNum(c.total)}</td>
                      <td>
                        <span
                          style={{
                            fontWeight: 600,
                            color:
                              c.avg_csat >= 4
                                ? "var(--accent-green)"
                                : c.avg_csat >= 3
                                ? "var(--accent-amber)"
                                : "var(--accent-red)",
                          }}
                        >
                          {c.avg_csat || "—"}
                        </span>
                      </td>
                      <td>{c.sla_breaches}</td>
                      <td>
                        <span
                          className={`badge ${c.breach_rate > 10 ? "red" : c.breach_rate > 5 ? "amber" : "green"}`}
                        >
                          {formatPct(c.breach_rate)}
                        </span>
                      </td>
                      <td>{c.avg_response_minutes != null ? `${c.avg_response_minutes}m` : "—"}</td>
                      <td>{formatNum(c.refund_count)}</td>
                      <td>{formatINR(c.total_refunds)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

