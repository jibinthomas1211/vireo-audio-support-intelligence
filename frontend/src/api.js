/**
 * api.js — API client for Vireo Audio Support Analytics backend.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function fetchJSON(path) {
  const url = `${BASE_URL}${path}`;
  const started = performance.now();
  console.info(`[api] GET ${path} started`);
  try {
    const res = await fetch(url);
    const durationMs = Math.round(performance.now() - started);
    console.info(`[api] GET ${path} -> ${res.status} (${durationMs}ms)`);
    if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
    return res.json();
  } catch (error) {
    const durationMs = Math.round(performance.now() - started);
    console.error(`[api] GET ${path} failed after ${durationMs}ms`, error);
    throw error;
  }
}

export const api = {
  getOverview: () => fetchJSON("/api/overview"),
  getWeeks: () => fetchJSON("/api/weeks"),
  getTeams: () => fetchJSON("/api/teams"),
  getDigest: (weekKey) => fetchJSON(`/api/digest/${encodeURIComponent(weekKey)}`),
  getLeaderboard: (params = {}) => {
    const query = new URLSearchParams();
    if (params.week) query.set("week", params.week);
    if (params.team) query.set("team", params.team);
    const qs = query.toString();
    return fetchJSON(`/api/leaderboard${qs ? `?${qs}` : ""}`);
  },
  getInsights: () => fetchJSON("/api/insights"),
  getTrends: () => fetchJSON("/api/trends"),
  getData: (resource, query = "") => fetchJSON(`/api/data/${resource}${query ? `?q=${encodeURIComponent(query)}` : ""}`),
};
