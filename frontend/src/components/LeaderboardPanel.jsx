import { useCallback, useState } from "react";
import { api } from "../api";
import {
  useApi,
} from "./shared";
import { formatINR, formatNum } from "./formatters";
import { Loading, ErrorDisplay } from "./ui";

function RankBadge({ rank }) {
  const cls =
    rank === 1 ? "gold" : rank === 2 ? "silver" : rank === 3 ? "bronze" : "default";
  return <span className={`rank-badge ${cls}`}>{rank}</span>;
}

function CSATBar({ value }) {
  if (value == null) return <span style={{ color: "var(--text-muted)" }}>—</span>;
  const pct = (value / 5) * 100;
  const color =
    value >= 4 ? "var(--accent-green)" : value >= 3 ? "var(--accent-amber)" : "var(--accent-red)";
  return (
    <div className="csat-bar">
      <div
        className="csat-fill"
        style={{
          width: `${pct}%`,
          maxWidth: 60,
          background: color,
        }}
      />
      <span className="csat-value" style={{ color }}>
        {value}
      </span>
    </div>
  );
}

function AgentTable({ agents, tier }) {
  if (!agents?.length) {
    return <div className="empty-state">No agents found for this filter.</div>;
  }

  const isTier2 = tier === 2;

  return (
    <div className="table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            <th style={{ width: 50 }}>Rank</th>
            <th>Agent</th>
            <th>Team</th>
            <th>Site</th>
            <th>Shift</th>
            {isTier2 ? (
              <>
                <th>Avg CSAT</th>
                <th>Avg Resolution (hrs)</th>
                <th>Tickets</th>
              </>
            ) : (
              <>
                <th>Tickets Resolved</th>
                <th>Avg CSAT</th>
                <th>Avg Response (min)</th>
              </>
            )}
            <th>SLA Breaches</th>
            <th>Transfers</th>
            <th>Refunds</th>
          </tr>
        </thead>
        <tbody>
          {agents.map((agent) => (
            <tr key={agent.agent_id}>
              <td className="rank-cell">
                <RankBadge rank={agent.rank} />
              </td>
              <td>
                <div className="agent-name">{agent.name}</div>
                <div className="agent-team">{agent.agent_id}</div>
              </td>
              <td>{agent.team}</td>
              <td>
                <span className={`badge ${agent.site === "Bengaluru" ? "teal" : "purple"}`}>
                  {agent.site}
                </span>
              </td>
              <td>
                <span className="badge blue">{agent.shift}</span>
              </td>
              {isTier2 ? (
                <>
                  <td>
                    <CSATBar value={agent.avg_csat} />
                  </td>
                  <td style={{ fontWeight: 600 }}>
                    {agent.avg_resolution_hours != null ? `${agent.avg_resolution_hours}h` : "—"}
                  </td>
                  <td>{formatNum(agent.tickets_resolved)}</td>
                </>
              ) : (
                <>
                  <td style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "1rem" }}>
                    {formatNum(agent.tickets_resolved)}
                  </td>
                  <td>
                    <CSATBar value={agent.avg_csat} />
                  </td>
                  <td>
                    {agent.avg_response_minutes != null ? `${agent.avg_response_minutes}m` : "—"}
                  </td>
                </>
              )}
              <td>
                {agent.sla_breaches > 0 ? (
                  <span className="badge red">{agent.sla_breaches}</span>
                ) : (
                  <span className="badge green">0</span>
                )}
              </td>
              <td>{agent.total_transfers}</td>
              <td>{formatINR(agent.total_refunds)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function LeaderboardPanel() {
  const { data: weeks } = useApi(api.getWeeks);
  const { data: teams } = useApi(api.getTeams);

  const [selectedWeek, setSelectedWeek] = useState("");
  const [selectedTeam, setSelectedTeam] = useState("");
  const fetchLeaderboard = useCallback(() => api.getLeaderboard({
      week: selectedWeek || undefined,
      team: selectedTeam || undefined,
    }), [selectedWeek, selectedTeam]);
  const {
    data: leaderboard,
    loading,
    error,
  } = useApi(fetchLeaderboard);

  return (
    <div className="fade-in">
      {/* Filters */}
      <div className="filter-bar">
        <div className="filter-group">
          <div className="filter-label">Week</div>
          <select
            className="select-input"
            value={selectedWeek}
            onChange={(e) => setSelectedWeek(e.target.value)}
          >
            <option value="">All Time</option>
            {weeks?.map((w) => (
              <option key={w.week_key} value={w.week_key}>
                {w.week_key}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-group">
          <div className="filter-label">Team</div>
          <select
            className="select-input"
            value={selectedTeam}
            onChange={(e) => setSelectedTeam(e.target.value)}
          >
            <option value="">All Teams</option>
            {teams?.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        {selectedWeek && (
          <div style={{ alignSelf: "flex-end" }}>
            <button className="nav-btn" onClick={() => setSelectedWeek("")}>
              ✕ Clear week filter
            </button>
          </div>
        )}
      </div>

      {loading && <Loading text="Loading leaderboard..." />}
      {error && <ErrorDisplay message={error} />}

      {leaderboard && !loading && (
        <>
          {/* Tier 1: Frontline Agents */}
          <div className="section-card">
            <div className="section-header">
              <h2>
                🏆 Tier 1 — Frontline Agents
                <span className="badge teal" style={{ marginLeft: 8 }}>
                  {leaderboard.tier1.length} agents
                </span>
              </h2>
              <div className="tier-label">
                Ranked by tickets resolved · Volume metric
              </div>
            </div>
            <div className="section-body" style={{ padding: 0 }}>
              <AgentTable agents={leaderboard.tier1} tier={1} />
            </div>
          </div>

          {/* Tier 2: Escalations & Warranty */}
          {leaderboard.tier2.length > 0 && (
            <div className="section-card">
              <div className="section-header">
                <h2>
                  🛡️ Tier 2 — Escalations & Warranty
                  <span className="badge purple" style={{ marginLeft: 8 }}>
                    {leaderboard.tier2.length} agents
                  </span>
                </h2>
                <div className="tier-label t2">
                  Ranked by CSAT & resolution quality · Not volume
                </div>
              </div>
              <div className="section-body" style={{ padding: 0 }}>
                <AgentTable agents={leaderboard.tier2} tier={2} />
              </div>
              <div
                style={{
                  padding: "12px 24px",
                  background: "var(--accent-purple-dim)",
                  borderTop: "1px solid var(--border-subtle)",
                  fontSize: "0.78rem",
                  color: "var(--accent-purple)",
                }}
              >
                ℹ️ Per policy §6: Tier 2 cases are multi-touch by nature. These agents are measured on resolution quality and CSAT, not on tickets closed per week.
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
