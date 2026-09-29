export function formatINR(amount) {
  if (amount == null) return "—";
  return "₹" + Number(amount).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

export function formatNum(n) {
  if (n == null) return "—";
  return Number(n).toLocaleString("en-IN");
}

export function formatPct(n) {
  if (n == null) return "—";
  return `${n}%`;
}

export const CHART_COLORS = [
  "#2864e8",
  "#6f91c5",
  "#91a8c8",
  "#b1bfd1",
  "#d2dbe7",
  "#4e78b5",
  "#d97083",
  "#e8a83e",
  "#7c9bc7",
  "#aabbd3",
  "#c0cad8",
];