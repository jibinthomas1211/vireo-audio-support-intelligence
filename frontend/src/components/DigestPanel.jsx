import { useCallback, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell,
} from "recharts";
import Markdown from "react-markdown";
import { api } from "../api";
import {
  useApi,
} from "./shared";
import { formatINR, CHART_COLORS } from "./formatters";
import { Loading, ErrorDisplay } from "./ui";

function formatDigestNarrative(narrative = "") {
  const sectionPattern = /^(?:\s*\d+[.)]\s*)?\*{0,2}(Executive Summary|Top Complaint Themes|Product Spotlight|Operational Flags|Recommended Actions)\*{0,2}\s*(.*)$/i;

  return narrative
    .split("\n")
    .flatMap((line) => {
      const match = line.match(sectionPattern);
      if (!match) return [line];
      return [`## ${match[1]}`, match[2].trim(), ""];
    })
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

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
        </div>
      ))}
    </div>
  );
};

export default function DigestPanel() {
  const { data: weeks, loading: loadingWeeks } = useApi(api.getWeeks);
  const [selectedWeek, setSelectedWeek] = useState(null);
  const effectiveWeek = selectedWeek || weeks?.[weeks.length - 1]?.week_key;
  const fetchDigest = useCallback(() => api.getDigest(effectiveWeek), [effectiveWeek]);
  const {
    data: digest,
    loading: loadingDigest,
    error: digestError,
  } = useApi(fetchDigest, Boolean(effectiveWeek));
  const digestPending = loadingDigest || !digest || digest.week_key !== effectiveWeek;

  if (loadingWeeks) return <Loading text="Loading weeks..." />;

  return (
    <div className="fade-in">
      {/* Week Selector */}
      <div className="filter-bar">
        <div className="filter-group">
          <div className="filter-label">Select Week</div>
          <select
            className="select-input"
            value={effectiveWeek || ""}
            onChange={(e) => setSelectedWeek(e.target.value)}
          >
            {weeks?.map((w) => (
              <option key={w.week_key} value={w.week_key}>
                {w.week_key} — {w.ticket_count} tickets
              </option>
            ))}
          </select>
        </div>
      </div>

      {digestPending && <Loading text="Generating weekly digest..." />}
      {digestError && <ErrorDisplay message={digestError} />}

      {digest && !digestPending && (
        <>
          {/* Quick Stats */}
          <div className="digest-stats-grid">
            <div className="digest-stat">
              <div className="digest-stat-value" style={{ color: "var(--accent-teal)" }}>
                {digest.stats.total}
              </div>
              <div className="digest-stat-label">Tickets</div>
            </div>
            <div className="digest-stat">
              <div className="digest-stat-value" style={{ color: "var(--accent-green)" }}>
                {digest.stats.resolved}
              </div>
              <div className="digest-stat-label">Resolved</div>
            </div>
            <div className="digest-stat">
              <div className="digest-stat-value" style={{ color: "var(--accent-red)" }}>
                {digest.stats.sla_breaches}
              </div>
              <div className="digest-stat-label">SLA Breaches</div>
            </div>
            <div className="digest-stat">
              <div
                className="digest-stat-value"
                style={{
                  color: digest.stats.avg_csat >= 4 ? "var(--accent-green)" : digest.stats.avg_csat >= 3 ? "var(--accent-amber)" : "var(--accent-red)",
                }}
              >
                {digest.stats.avg_csat || "—"}
              </div>
              <div className="digest-stat-label">Avg CSAT</div>
            </div>
            <div className="digest-stat">
              <div className="digest-stat-value" style={{ color: "var(--accent-amber)" }}>
                {digest.stats.repeat_contacts}
              </div>
              <div className="digest-stat-label">Repeat Contacts</div>
            </div>
            <div className="digest-stat">
              <div className="digest-stat-value">
                {formatINR(digest.stats.total_refunds)}
              </div>
              <div className="digest-stat-label">Refunds</div>
            </div>
            <div className="digest-stat">
              <div className="digest-stat-value">{digest.stats.replacements}</div>
              <div className="digest-stat-label">Replacements</div>
            </div>
            <div className="digest-stat">
              <div className="digest-stat-value">
                {digest.stats.avg_response_minutes ? `${digest.stats.avg_response_minutes}m` : "—"}
              </div>
              <div className="digest-stat-label">Avg Response</div>
            </div>
          </div>

          <div className="chart-grid">
            {/* AI Narrative */}
            <div className="section-card" style={{ gridColumn: "1 / -1" }}>
              <div className="section-header">
                <h2>📝 Weekly Summary</h2>
                {digest.ai_summary && (
                  <span className={`ai-badge ${digest.ai_summary.source === "ai" ? "ai" : "rule"}`}>
                    {digest.ai_summary.source === "ai" ? "✨ AI Generated" : "📊 Rule-Based"}
                    {digest.ai_summary.model && ` · ${digest.ai_summary.model}`}
                  </span>
                )}
              </div>
              <div className="section-body">
                <div className="digest-content">
                  <Markdown>{formatDigestNarrative(digest.ai_summary?.narrative || "No summary available.")}</Markdown>
                </div>
              </div>
            </div>

            {/* Category Breakdown */}
            <div className="section-card">
              <div className="section-header">
                <h2>🏷️ Tickets by Category</h2>
              </div>
              <div className="section-body">
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={digest.categories}
                      layout="vertical"
                      margin={{ left: 120 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                      <XAxis type="number" tick={{ fill: "#5c6478", fontSize: 11 }} axisLine={{ stroke: "rgba(255,255,255,0.06)" }} />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fill: "#8a92a8", fontSize: 11 }}
                        axisLine={false}
                        width={120}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="count" name="Tickets" radius={[0, 4, 4, 0]}>
                        {digest.categories.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} opacity={0.8} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            {/* Channel Breakdown */}
            <div className="section-card">
              <div className="section-header">
                <h2>📡 Tickets by Channel</h2>
              </div>
              <div className="section-body">
                <div className="chart-container" style={{ display: "flex", alignItems: "center" }}>
                  <ResponsiveContainer width="55%" height="100%">
                    <PieChart>
                      <Pie
                        data={digest.channels}
                        dataKey="count"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={85}
                        stroke="none"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      >
                        {digest.channels.map((_, i) => (
                          <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip content={<CustomTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
                    {digest.channels.map((ch, i) => (
                      <div key={ch.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <div
                            style={{
                              width: 10,
                              height: 10,
                              borderRadius: 3,
                              background: CHART_COLORS[i % CHART_COLORS.length],
                            }}
                          />
                          <span style={{ fontSize: "0.82rem", color: "#8a92a8" }}>{ch.name}</span>
                        </div>
                        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                          <span style={{ fontSize: "0.82rem", fontWeight: 600, color: "#f0f2f8" }}>
                            {ch.count}
                          </span>
                          {ch.sla_breaches > 0 && (
                            <span className="badge red">{ch.sla_breaches} breaches</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Product Breakdown */}
            <div className="section-card" style={{ gridColumn: "1 / -1" }}>
              <div className="section-header">
                <h2>📦 Tickets by Product</h2>
              </div>
              <div className="section-body">
                <div className="cat-bar-container">
                  {digest.products.map((prod, i) => {
                    const maxCount = digest.products[0]?.count || 1;
                    const pct = (prod.count / maxCount) * 100;
                    return (
                      <div className="cat-bar-item" key={prod.sku}>
                        <div className="cat-bar-label" title={prod.sku}>
                          {prod.name || prod.sku}
                        </div>
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
                        <div className="cat-bar-value">
                          {prod.count}
                          {prod.avg_csat && (
                            <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginLeft: 6 }}>
                              ⭐{prod.avg_csat}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
