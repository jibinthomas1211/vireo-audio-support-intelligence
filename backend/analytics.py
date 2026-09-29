"""
analytics.py — Query engine for Vireo Audio support ticket metrics.

Provides functions for:
  - Weekly digest data (volume, categories, SLA, CSAT, top issues)
  - Agent leaderboard (tier-aware: Tier 1 by volume, Tier 2 by quality)
  - Insights (repeat contacts, SLA trends, refund anomalies, transfers)
  - Trend data over time
"""

import sqlite3
from data_loader import SLA_TARGETS, BLENDED_COST, SLA_BREACH_CREDIT, TRANSFER_COST


def get_available_weeks(conn: sqlite3.Connection) -> list[dict]:
    """Return all available week keys with their ticket counts."""
    rows = conn.execute("""
        SELECT week_key,
               MIN(created_at) as week_start,
               MAX(created_at) as week_end,
               COUNT(*) as ticket_count
        FROM tickets
        WHERE is_duplicate = 0 AND week_key IS NOT NULL
        GROUP BY week_key
        ORDER BY week_key
    """).fetchall()

    return [
        {
            "week_key": r["week_key"],
            "week_start": r["week_start"],
            "week_end": r["week_end"],
            "ticket_count": r["ticket_count"],
        }
        for r in rows
    ]


def get_weekly_digest_data(conn: sqlite3.Connection, week_key: str) -> dict:
    """Get comprehensive data for a given week's digest."""

    # Basic stats
    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status IN ('resolved','closed') THEN 1 ELSE 0 END) as resolved,
            SUM(sla_breached) as sla_breaches,
            AVG(CASE WHEN csat_score IS NOT NULL THEN csat_score END) as avg_csat,
            AVG(response_minutes) as avg_response_min,
            AVG(CASE WHEN resolution_hours > 0 THEN resolution_hours END) as avg_resolution_hrs,
            SUM(CASE WHEN refund_amount_inr IS NOT NULL THEN refund_amount_inr ELSE 0 END) as total_refunds,
            SUM(CASE WHEN replacement_issued = 'Y' THEN 1 ELSE 0 END) as replacements,
            SUM(transfers) as total_transfers
        FROM tickets
        WHERE week_key = ? AND is_duplicate = 0
    """, (week_key,)).fetchone()

    # Category breakdown
    categories = conn.execute("""
        SELECT category, COUNT(*) as cnt,
               AVG(CASE WHEN csat_score IS NOT NULL THEN csat_score END) as avg_csat,
               SUM(sla_breached) as breaches
        FROM tickets
        WHERE week_key = ? AND is_duplicate = 0
        GROUP BY category
        ORDER BY cnt DESC
    """, (week_key,)).fetchall()

    # Channel breakdown
    channels = conn.execute("""
        SELECT channel, COUNT(*) as cnt,
               SUM(sla_breached) as breaches,
               AVG(response_minutes) as avg_response_min
        FROM tickets
        WHERE week_key = ? AND is_duplicate = 0
        GROUP BY channel
        ORDER BY cnt DESC
    """, (week_key,)).fetchall()

    # Product breakdown
    products = conn.execute("""
        SELECT t.product_sku, p.product_name, p.family, COUNT(*) as cnt,
               AVG(CASE WHEN t.csat_score IS NOT NULL THEN t.csat_score END) as avg_csat
        FROM tickets t
        LEFT JOIN products p ON t.product_sku = p.sku
        WHERE t.week_key = ? AND t.is_duplicate = 0
        GROUP BY t.product_sku
        ORDER BY cnt DESC
    """, (week_key,)).fetchall()

    # Priority breakdown
    priorities = conn.execute("""
        SELECT priority, COUNT(*) as cnt
        FROM tickets
        WHERE week_key = ? AND is_duplicate = 0
        GROUP BY priority
    """, (week_key,)).fetchall()

    # Sample customer messages for AI summarization (up to 80)
    messages = conn.execute("""
        SELECT customer_message, agent_notes, category, product_sku, channel
        FROM tickets
        WHERE week_key = ? AND is_duplicate = 0
        AND customer_message IS NOT NULL AND customer_message != ''
        ORDER BY ticket_id
        LIMIT 80
    """, (week_key,)).fetchall()

    # Repeat contacts for this week
    repeats_in_week = conn.execute("""
        SELECT COUNT(*) as cnt FROM repeat_contacts rc
        JOIN tickets t ON rc.original_ticket_id = t.ticket_id
        WHERE t.week_key = ? AND t.is_duplicate = 0
    """, (week_key,)).fetchone()

    return {
        "week_key": week_key,
        "stats": {
            "total": stats["total"],
            "resolved": stats["resolved"],
            "sla_breaches": stats["sla_breaches"],
            "sla_breach_rate": round((stats["sla_breaches"] / stats["total"]) * 100, 1) if stats["total"] else 0,
            "avg_csat": round(stats["avg_csat"], 2) if stats["avg_csat"] is not None else None,
            "avg_response_minutes": round(stats["avg_response_min"], 1) if stats["avg_response_min"] is not None else None,
            "avg_resolution_hours": round(stats["avg_resolution_hrs"], 1) if stats["avg_resolution_hrs"] is not None else None,
            "total_refunds": round(stats["total_refunds"] or 0, 0),
            "replacements": stats["replacements"],
            "total_transfers": stats["total_transfers"],
            "repeat_contacts": repeats_in_week["cnt"],
        },
        "categories": [
            {
                "name": r["category"],
                "count": r["cnt"],
                "avg_csat": round(r["avg_csat"], 2) if r["avg_csat"] is not None else None,
                "sla_breaches": r["breaches"],
            }
            for r in categories
        ],
        "channels": [
            {
                "name": r["channel"],
                "count": r["cnt"],
                "sla_breaches": r["breaches"],
                "avg_response_minutes": round(r["avg_response_min"], 1) if r["avg_response_min"] is not None else None,
            }
            for r in channels
        ],
        "products": [
            {
                "sku": r["product_sku"],
                "name": r["product_name"],
                "family": r["family"],
                "count": r["cnt"],
                "avg_csat": round(r["avg_csat"], 2) if r["avg_csat"] is not None else None,
            }
            for r in products
        ],
        "priorities": {r["priority"]: r["cnt"] for r in priorities},
        "sample_messages": [
            {
                "message": r["customer_message"][:300],
                "notes": r["agent_notes"][:300] if r["agent_notes"] else "",
                "category": r["category"],
                "product": r["product_sku"],
                "channel": r["channel"],
            }
            for r in messages
        ],
    }


def get_agent_leaderboard(conn: sqlite3.Connection, week_key: str = None, team: str = None) -> dict:
    """
    Agent leaderboard with tier-aware ranking.
    Tier 1: ranked by tickets resolved (with CSAT overlay).
    Tier 2 (Escalations & Warranty): ranked by avg CSAT and resolution quality, NOT volume.
    """

    where_clauses = ["t.is_duplicate = 0", "t.status IN ('resolved','closed')"]
    params = []

    if week_key:
        where_clauses.append("t.week_key = ?")
        params.append(week_key)

    if team:
        where_clauses.append("t.assigned_team = ?")
        params.append(team)

    where_sql = " AND ".join(where_clauses)

    rows = conn.execute(f"""
        SELECT
            t.agent_id,
            a.name as agent_name,
            a.team,
            a.site,
            a.shift,
            a.tier as agent_tier,
            COUNT(*) as tickets_resolved,
            AVG(CASE WHEN t.csat_score IS NOT NULL THEN t.csat_score END) as avg_csat,
            SUM(t.sla_breached) as sla_breaches,
            AVG(CASE WHEN t.resolution_hours > 0 THEN t.resolution_hours END) as avg_resolution_hrs,
            AVG(t.response_minutes) as avg_response_min,
            SUM(t.transfers) as total_transfers,
            SUM(CASE WHEN t.refund_amount_inr IS NOT NULL THEN t.refund_amount_inr ELSE 0 END) as total_refunds
        FROM tickets t
        LEFT JOIN agents a ON t.agent_id = a.agent_id
        WHERE {where_sql}
        GROUP BY t.agent_id
        ORDER BY a.tier, tickets_resolved DESC
    """, params).fetchall()

    tier1 = []
    tier2 = []

    for r in rows:
        agent_data = {
            "agent_id": r["agent_id"],
            "name": r["agent_name"],
            "team": r["team"],
            "site": r["site"],
            "shift": r["shift"],
            "tickets_resolved": r["tickets_resolved"],
            "avg_csat": round(r["avg_csat"], 2) if r["avg_csat"] is not None else None,
            "sla_breaches": r["sla_breaches"],
            "avg_resolution_hours": round(r["avg_resolution_hrs"], 1) if r["avg_resolution_hrs"] else None,
            "avg_response_minutes": round(r["avg_response_min"], 1) if r["avg_response_min"] else None,
            "total_transfers": r["total_transfers"],
            "total_refunds": round(r["total_refunds"] or 0, 0),
        }

        if r["agent_tier"] == 2:
            tier2.append(agent_data)
        else:
            tier1.append(agent_data)

    # Sort Tier 1 by tickets resolved (descending)
    tier1.sort(key=lambda x: x["tickets_resolved"], reverse=True)

    # Sort Tier 2 by avg CSAT (descending), then resolution hours (ascending)
    tier2.sort(
        key=lambda x: (-(x["avg_csat"] or 0), x["avg_resolution_hours"] or 9999)
    )

    # Add rank
    for i, agent in enumerate(tier1, 1):
        agent["rank"] = i
    for i, agent in enumerate(tier2, 1):
        agent["rank"] = i

    return {
        "week_key": week_key,
        "team_filter": team,
        "tier1": tier1,
        "tier2": tier2,
        "tier1_count": len(tier1),
        "tier2_count": len(tier2),
    }


def get_available_teams(conn: sqlite3.Connection) -> list[str]:
    """Return list of unique team names."""
    rows = conn.execute("""
        SELECT DISTINCT assigned_team FROM tickets WHERE is_duplicate = 0 ORDER BY assigned_team
    """).fetchall()
    return [r["assigned_team"] for r in rows]


def get_insights(conn: sqlite3.Connection) -> dict:
    """Get data for the insights panel: repeat contacts, SLA trends, refund anomalies."""

    # Repeat contact trend by week
    repeat_trend = conn.execute("""
        SELECT t.week_key,
               COUNT(DISTINCT rc.original_ticket_id) as repeat_count,
               (SELECT COUNT(*) FROM tickets t2
                WHERE t2.week_key = t.week_key AND t2.is_duplicate = 0
                AND t2.status IN ('resolved','closed')) as resolved_count
        FROM repeat_contacts rc
        JOIN tickets t ON rc.original_ticket_id = t.ticket_id
        WHERE t.is_duplicate = 0
        GROUP BY t.week_key
        ORDER BY t.week_key
    """).fetchall()

    # SLA breach trend by week
    sla_trend = conn.execute("""
        SELECT week_key,
               COUNT(*) as total,
               SUM(sla_breached) as breaches
        FROM tickets
        WHERE is_duplicate = 0 AND week_key IS NOT NULL
        GROUP BY week_key
        ORDER BY week_key
    """).fetchall()

    # Refund anomalies: refund + replacement on same ticket
    anomalies = conn.execute("""
        SELECT t.ticket_id, t.created_at, t.customer_id, t.product_sku,
               p.product_name, t.refund_amount_inr, t.refund_reason_code,
               t.agent_id, a.name as agent_name
        FROM tickets t
        LEFT JOIN products p ON t.product_sku = p.sku
        LEFT JOIN agents a ON t.agent_id = a.agent_id
        WHERE t.is_duplicate = 0
        AND t.refund_amount_inr IS NOT NULL
        AND t.replacement_issued = 'Y'
    """).fetchall()

    # Top transfer routes (teams generating most transfers)
    transfer_teams = conn.execute("""
        SELECT assigned_team, SUM(transfers) as total_transfers,
               COUNT(*) as tickets,
               ROUND(AVG(transfers), 2) as avg_transfers
        FROM tickets
        WHERE is_duplicate = 0 AND transfers > 0
        GROUP BY assigned_team
        ORDER BY total_transfers DESC
    """).fetchall()

    # CSAT distribution (excluding nulls and legacy 0s)
    csat_dist = conn.execute("""
        SELECT csat_score, COUNT(*) as cnt
        FROM tickets
        WHERE is_duplicate = 0 AND csat_score IS NOT NULL
        GROUP BY csat_score
        ORDER BY csat_score
    """).fetchall()

    # Category-level insights
    category_insights = conn.execute("""
        SELECT category,
               COUNT(*) as total,
               AVG(CASE WHEN csat_score IS NOT NULL THEN csat_score END) as avg_csat,
               SUM(sla_breached) as breaches,
               AVG(response_minutes) as avg_response_min,
               SUM(CASE WHEN refund_amount_inr IS NOT NULL THEN 1 ELSE 0 END) as refund_count,
               SUM(CASE WHEN refund_amount_inr IS NOT NULL THEN refund_amount_inr ELSE 0 END) as total_refunds
        FROM tickets
        WHERE is_duplicate = 0
        GROUP BY category
        ORDER BY total DESC
    """).fetchall()

    return {
        "repeat_contact_trend": [
            {
                "week": r["week_key"],
                "repeat_count": r["repeat_count"],
                "resolved_count": r["resolved_count"],
                "rate": round((r["repeat_count"] / r["resolved_count"]) * 100, 1) if r["resolved_count"] else 0,
            }
            for r in repeat_trend
        ],
        "sla_breach_trend": [
            {
                "week": r["week_key"],
                "total": r["total"],
                "breaches": r["breaches"],
                "rate": round((r["breaches"] / r["total"]) * 100, 1) if r["total"] else 0,
            }
            for r in sla_trend
        ],
        "refund_replacement_anomalies": [
            {
                "ticket_id": r["ticket_id"],
                "created_at": r["created_at"],
                "customer_id": r["customer_id"],
                "product_sku": r["product_sku"],
                "product_name": r["product_name"],
                "refund_amount": r["refund_amount_inr"],
                "reason_code": r["refund_reason_code"],
                "agent_id": r["agent_id"],
                "agent_name": r["agent_name"],
            }
            for r in anomalies
        ],
        "transfer_by_team": [
            {
                "team": r["assigned_team"],
                "total_transfers": r["total_transfers"],
                "tickets_with_transfers": r["tickets"],
                "avg_transfers": r["avg_transfers"],
                "transfer_cost": r["total_transfers"] * TRANSFER_COST,
            }
            for r in transfer_teams
        ],
        "csat_distribution": [
            {"score": r["csat_score"], "count": r["cnt"]}
            for r in csat_dist
        ],
        "category_insights": [
            {
                "category": r["category"],
                "total": r["total"],
                "avg_csat": round(r["avg_csat"], 2) if r["avg_csat"] is not None else None,
                "sla_breaches": r["breaches"],
                "breach_rate": round((r["breaches"] / r["total"]) * 100, 1) if r["total"] else 0,
                "avg_response_minutes": round(r["avg_response_min"], 1) if r["avg_response_min"] is not None else None,
                "refund_count": r["refund_count"],
                "total_refunds": round(r["total_refunds"] or 0, 0),
            }
            for r in category_insights
        ],
    }


def get_weekly_volume_trend(conn: sqlite3.Connection) -> list[dict]:
    """Get ticket volume trend by week for sparkline charts."""
    rows = conn.execute("""
        SELECT week_key,
               COUNT(*) as total,
               SUM(CASE WHEN status IN ('resolved','closed') THEN 1 ELSE 0 END) as resolved,
               SUM(sla_breached) as breaches,
               AVG(CASE WHEN csat_score IS NOT NULL THEN csat_score END) as avg_csat
        FROM tickets
        WHERE is_duplicate = 0 AND week_key IS NOT NULL
        GROUP BY week_key
        ORDER BY week_key
    """).fetchall()

    return [
        {
            "week": r["week_key"],
            "total": r["total"],
            "resolved": r["resolved"],
            "breaches": r["breaches"],
            "avg_csat": round(r["avg_csat"], 2) if r["avg_csat"] is not None else None,
        }
        for r in rows
    ]
