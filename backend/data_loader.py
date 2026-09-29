"""
data_loader.py — Loads Vireo Audio CSVs into an in-memory SQLite database.

Handles:
  - Freshdesk migration duplicates (653 ticket IDs appear in both helpdesk & legacy_fd)
  - CSAT "0" → NULL (policy §8: blank/0 = no response, exclude from averages)
  - Derived fields: response_minutes, resolution_hours, sla_breached, is_repeat_contact
  - Legacy timestamp flag (resolved_at < created_at due to UTC→IST mismatch §9)
"""

import csv
import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path


# SLA targets from support-policy.pdf §3 (in minutes)
SLA_TARGETS = {"chat": 15, "voice": 120, "social": 240, "email": 480}

# Cost standards from support-policy.pdf §4
COST_PER_CONTACT = {"chat": 210, "email": 260, "voice": 520, "social": 240}
BLENDED_COST = 290
TRANSFER_COST = 305
SLA_BREACH_CREDIT = 350


def find_data_dir():
    """Locate the files/ directory relative to backend/."""
    base = Path(__file__).resolve().parent.parent / "files"
    if base.exists():
        return base
    raise FileNotFoundError(f"Data directory not found at {base}")


def find_csv(data_dir: Path, suffix: str) -> Path:
    """Find a CSV file by its suffix name (e.g., 'tickets' matches '*-tickets.csv')."""
    matches = list(data_dir.glob(f"*-{suffix}.csv"))
    if not matches:
        matches = list(data_dir.glob(f"{suffix}.csv"))
    if not matches:
        raise FileNotFoundError(f"No CSV matching '*{suffix}.csv' in {data_dir}")
    return matches[0]


def parse_timestamp(ts_str: str):
    """Parse the timestamp formats found in the export."""
    if not ts_str or not ts_str.strip():
        return None
    ts_str = ts_str.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None


def init_database() -> sqlite3.Connection:
    """Create in-memory SQLite database and load all data."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    data_dir = find_data_dir()

    _create_tables(conn)
    _load_products(conn, data_dir)
    _load_agents(conn, data_dir)
    _load_customers(conn, data_dir)
    _load_orders(conn, data_dir)
    _load_tickets(conn, data_dir)
    _compute_derived_fields(conn)

    return conn


def _create_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE products (
            sku TEXT PRIMARY KEY,
            product_name TEXT,
            family TEXT,
            launch_date TEXT,
            unit_cost_inr REAL,
            retail_price_inr REAL,
            warranty_months INTEGER
        );

        CREATE TABLE agents (
            agent_id TEXT,
            name TEXT,
            site TEXT,
            team TEXT,
            shift TEXT,
            tier INTEGER,
            from_date TEXT,
            to_date TEXT
        );

        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT,
            city TEXT,
            state TEXT,
            signup_date TEXT,
            care_plus TEXT
        );

        CREATE TABLE orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            sku TEXT,
            order_date TEXT,
            channel TEXT,
            qty INTEGER,
            order_value_inr REAL,
            lot_code TEXT
        );

        CREATE TABLE tickets (
            ticket_id TEXT,
            created_at TEXT,
            first_response_at TEXT,
            resolved_at TEXT,
            status TEXT,
            channel TEXT,
            customer_id TEXT,
            order_id TEXT,
            product_sku TEXT,
            category TEXT,
            priority TEXT,
            assigned_team TEXT,
            agent_id TEXT,
            transfers INTEGER DEFAULT 0,
            csat_score INTEGER,
            refund_amount_inr REAL,
            refund_reason_code TEXT,
            replacement_issued TEXT,
            customer_message TEXT,
            agent_notes TEXT,
            source_system TEXT,
            -- derived fields
            response_minutes REAL,
            resolution_hours REAL,
            sla_target_minutes REAL,
            sla_breached INTEGER DEFAULT 0,
            is_legacy_ts_issue INTEGER DEFAULT 0,
            is_duplicate INTEGER DEFAULT 0,
            week_key TEXT,
            agent_tier INTEGER DEFAULT 1
        );

        CREATE TABLE repeat_contacts (
            original_ticket_id TEXT,
            repeat_ticket_id TEXT,
            days_between REAL
        );
    """)


def _load_csv_rows(filepath: Path):
    """Read a CSV file and return list of dicts."""
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _load_products(conn: sqlite3.Connection, data_dir: Path):
    rows = _load_csv_rows(find_csv(data_dir, "products"))
    for r in rows:
        conn.execute(
            "INSERT INTO products VALUES (?,?,?,?,?,?,?)",
            (
                r["sku"], r["product_name"], r["family"],
                r["launch_date"],
                float(r["unit_cost_inr"]) if r.get("unit_cost_inr") else None,
                float(r["retail_price_inr"]) if r.get("retail_price_inr") else None,
                int(r["warranty_months"]) if r.get("warranty_months") else None,
            ),
        )
    conn.commit()


def _load_agents(conn: sqlite3.Connection, data_dir: Path):
    rows = _load_csv_rows(find_csv(data_dir, "agents"))
    for r in rows:
        tier = 2 if "Escalation" in r.get("team", "") or "Warranty" in r.get("team", "") else 1
        conn.execute(
            "INSERT INTO agents VALUES (?,?,?,?,?,?,?,?)",
            (
                r["agent_id"], r["name"], r["site"], r["team"],
                r["shift"], tier, r["from_date"], r.get("to_date", ""),
            ),
        )
    conn.commit()


def _load_customers(conn: sqlite3.Connection, data_dir: Path):
    rows = _load_csv_rows(find_csv(data_dir, "customers"))
    for r in rows:
        conn.execute(
            "INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?)",
            (
                r["customer_id"], r["name"], r["city"], r["state"],
                r["signup_date"], r.get("care_plus", "N"),
            ),
        )
    conn.commit()


def _load_orders(conn: sqlite3.Connection, data_dir: Path):
    rows = _load_csv_rows(find_csv(data_dir, "orders"))
    for r in rows:
        conn.execute(
            "INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?,?,?,?)",
            (
                r["order_id"], r["customer_id"], r.get("sku", ""),
                r["order_date"], r.get("channel", ""),
                int(r["qty"]) if r.get("qty") else 1,
                float(r["order_value_inr"]) if r.get("order_value_inr") else None,
                r.get("lot_code", ""),
            ),
        )
    conn.commit()


def _load_tickets(conn: sqlite3.Connection, data_dir: Path):
    rows = _load_csv_rows(find_csv(data_dir, "tickets"))

    # Identify duplicates: same ticket_id exists in both helpdesk and legacy_fd
    from collections import defaultdict
    id_sources = defaultdict(list)
    for r in rows:
        id_sources[r["ticket_id"]].append(r["source_system"])

    dup_ids = {
        tid for tid, sources in id_sources.items()
        if len(sources) > 1
    }

    seen_dup_ids = set()

    for r in rows:
        tid = r["ticket_id"]
        is_dup = 0

        # For duplicate IDs, keep only the helpdesk version
        if tid in dup_ids:
            if r["source_system"] == "legacy_fd":
                is_dup = 1
                if tid in seen_dup_ids:
                    continue  # skip this row entirely
            seen_dup_ids.add(tid)

        # Parse timestamps
        created = parse_timestamp(r["created_at"])
        responded = parse_timestamp(r["first_response_at"])
        resolved = parse_timestamp(r["resolved_at"])

        # Compute response time in minutes
        response_minutes = None
        if created and responded:
            response_minutes = (responded - created).total_seconds() / 60.0

        # Compute resolution time in hours
        resolution_hours = None
        is_legacy_ts = 0
        if created and resolved:
            delta = (resolved - created).total_seconds() / 3600.0
            if delta < 0:
                # Legacy UTC→IST issue (§9): resolved_at was stored in UTC
                is_legacy_ts = 1
                # Add 5.5 hours (IST offset) as best-effort fix
                delta = delta + 5.5
                if delta < 0:
                    delta = abs(delta)  # still negative → use absolute
            resolution_hours = delta

        # SLA breach check
        channel = r["channel"]
        sla_target = SLA_TARGETS.get(channel)
        sla_breached = 0
        if response_minutes is not None and sla_target is not None:
            if response_minutes > sla_target:
                sla_breached = 1

        # CSAT: convert "0" to NULL (policy §8)
        csat = r.get("csat_score", "").strip()
        if csat in ("", "0"):
            csat_val = None
        else:
            try:
                csat_val = int(csat)
            except ValueError:
                csat_val = None

        # Refund amount
        refund_str = r.get("refund_amount_inr", "").strip()
        refund_val = float(refund_str) if refund_str else None

        # Transfers
        transfers_str = r.get("transfers", "0").strip()
        transfers_val = int(transfers_str) if transfers_str else 0

        # Week key (ISO year-week)
        week_key = None
        if created:
            week_key = created.strftime("%Y-W%W")

        # Agent tier
        agent_tier = 1
        team = r.get("assigned_team", "")
        if "Escalation" in team or "Warranty" in team:
            agent_tier = 2

        conn.execute(
            """INSERT INTO tickets VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
            )""",
            (
                tid,
                r["created_at"], r["first_response_at"], r["resolved_at"],
                r["status"], channel, r["customer_id"],
                r.get("order_id", "").strip() or None,
                r["product_sku"], r["category"], r["priority"],
                r["assigned_team"], r["agent_id"],
                transfers_val, csat_val, refund_val,
                r.get("refund_reason_code", "").strip() or None,
                r.get("replacement_issued", "N"),
                r["customer_message"], r["agent_notes"],
                r["source_system"],
                response_minutes, resolution_hours,
                sla_target, sla_breached, is_legacy_ts, is_dup,
                week_key, agent_tier,
            ),
        )

    conn.commit()

    # Create indices for fast queries
    conn.executescript("""
        CREATE INDEX idx_tickets_week ON tickets(week_key);
        CREATE INDEX idx_tickets_agent ON tickets(agent_id);
        CREATE INDEX idx_tickets_status ON tickets(status);
        CREATE INDEX idx_tickets_customer ON tickets(customer_id);
        CREATE INDEX idx_tickets_category ON tickets(category);
        CREATE INDEX idx_tickets_channel ON tickets(channel);
        CREATE INDEX idx_tickets_sku ON tickets(product_sku);
        CREATE INDEX idx_tickets_created ON tickets(created_at);
    """)


def _compute_derived_fields(conn: sqlite3.Connection):
    """Compute repeat contacts (same customer, new ticket within 30 days of resolution)."""

    # Get all resolved tickets grouped by customer
    cursor = conn.execute("""
        SELECT ticket_id, customer_id, resolved_at, created_at, product_sku
        FROM tickets
        WHERE is_duplicate = 0
        AND status IN ('resolved', 'closed')
        AND resolved_at IS NOT NULL AND resolved_at != ''
        ORDER BY customer_id, created_at
    """)
    resolved = cursor.fetchall()

    # Get ALL tickets for lookup
    all_cursor = conn.execute("""
        SELECT ticket_id, customer_id, created_at, product_sku
        FROM tickets
        WHERE is_duplicate = 0
        ORDER BY customer_id, created_at
    """)
    all_tickets = all_cursor.fetchall()

    # Group by customer
    from collections import defaultdict
    customer_all = defaultdict(list)
    for t in all_tickets:
        customer_all[t["customer_id"]].append(t)

    repeat_pairs = []
    for t in resolved:
        cid = t["customer_id"]
        resolved_dt = parse_timestamp(t["resolved_at"])
        created_dt = parse_timestamp(t["created_at"])
        if not resolved_dt:
            continue
        if created_dt and resolved_dt < created_dt:
            # Repeat windows must use the same IST correction as resolution_hours.
            resolved_dt = resolved_dt + timedelta(hours=5.5)

        for other in customer_all.get(cid, []):
            if other["ticket_id"] == t["ticket_id"]:
                continue
            other_created = parse_timestamp(other["created_at"])
            if not other_created:
                continue
            days = (other_created - resolved_dt).total_seconds() / 86400.0
            if 0 < days <= 30:
                repeat_pairs.append((t["ticket_id"], other["ticket_id"], round(days, 2)))
                break  # one repeat per original ticket is enough

    for orig, rep, days in repeat_pairs:
        conn.execute(
            "INSERT INTO repeat_contacts VALUES (?,?,?)",
            (orig, rep, days),
        )
    conn.commit()


def get_overview_stats(conn: sqlite3.Connection) -> dict:
    """Get high-level KPIs for the dashboard header."""
    row = conn.execute("""
        SELECT
            COUNT(*) as total_tickets,
            SUM(CASE WHEN is_duplicate = 0 THEN 1 ELSE 0 END) as unique_tickets,
            SUM(CASE WHEN is_duplicate = 1 THEN 1 ELSE 0 END) as duplicate_tickets,
            SUM(CASE WHEN sla_breached = 1 AND is_duplicate = 0 THEN 1 ELSE 0 END) as sla_breaches,
            AVG(CASE WHEN csat_score IS NOT NULL AND is_duplicate = 0 THEN csat_score END) as avg_csat,
            SUM(CASE WHEN refund_amount_inr IS NOT NULL AND is_duplicate = 0 THEN refund_amount_inr ELSE 0 END) as total_refunds,
            SUM(CASE WHEN replacement_issued = 'Y' AND is_duplicate = 0 THEN 1 ELSE 0 END) as replacements,
            SUM(CASE WHEN refund_amount_inr IS NOT NULL AND replacement_issued = 'Y' AND is_duplicate = 0 THEN 1 ELSE 0 END) as refund_and_replacement,
            COUNT(DISTINCT CASE WHEN is_duplicate = 0 THEN customer_id END) as unique_customers
        FROM tickets
    """).fetchone()

    repeat_count = conn.execute("SELECT COUNT(*) FROM repeat_contacts").fetchone()[0]
    unique = row["unique_tickets"] or 1

    # Tickets by status
    status_rows = conn.execute("""
        SELECT status, COUNT(*) as cnt
        FROM tickets WHERE is_duplicate = 0
        GROUP BY status
    """).fetchall()

    # SLA breaches by channel
    breach_rows = conn.execute("""
        SELECT channel,
               COUNT(*) as total,
               SUM(sla_breached) as breached
        FROM tickets
        WHERE is_duplicate = 0
        GROUP BY channel
    """).fetchall()

    return {
        "total_tickets": row["total_tickets"],
        "unique_tickets": row["unique_tickets"],
        "duplicate_tickets": row["duplicate_tickets"],
        "sla_breaches": row["sla_breaches"],
        "sla_breach_rate": round((row["sla_breaches"] / unique) * 100, 1) if unique else 0,
        "sla_breach_cost": row["sla_breaches"] * SLA_BREACH_CREDIT,
        "avg_csat": round(row["avg_csat"], 2) if row["avg_csat"] else None,
        "total_refunds": round(row["total_refunds"] or 0, 2),
        "replacements": row["replacements"],
        "refund_and_replacement_violations": row["refund_and_replacement"],
        "unique_customers": row["unique_customers"],
        "repeat_contacts": repeat_count,
        "repeat_contact_rate": round((repeat_count / unique) * 100, 1) if unique else 0,
        "cost_per_contact_blended": BLENDED_COST,
        "repeat_contact_cost": repeat_count * BLENDED_COST,
        "status_breakdown": {r["status"]: r["cnt"] for r in status_rows},
        "breach_by_channel": {
            r["channel"]: {
                "total": r["total"],
                "breached": r["breached"],
                "rate": round((r["breached"] / r["total"]) * 100, 1) if r["total"] else 0,
            }
            for r in breach_rows
        },
    }
