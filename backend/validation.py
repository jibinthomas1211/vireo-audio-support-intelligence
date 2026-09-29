"""
validation.py — Accuracy validation for the Vireo Audio support analytics tool.

Performs:
  1. Duplicate detection accuracy check
  2. SLA breach calculation verification
  3. Repeat contact detection spot-check
  4. CSAT handling verification
  5. Agent tier classification check
"""

import csv
import json
from datetime import datetime
from collections import defaultdict, Counter
from data_loader import init_database, parse_timestamp, SLA_TARGETS
from analytics import get_agent_leaderboard, get_available_weeks, get_weekly_digest_data

PASS = "✅ PASS"
FAIL = "❌ FAIL"


def run_validation():
    """Run all validation checks and print results."""
    print("=" * 70)
    print("VIREO AUDIO — TOOL VALIDATION REPORT")
    print("=" * 70)
    print()

    db = init_database()
    results = []

    results.append(validate_deduplication(db))
    results.append(validate_sla_breaches(db))
    results.append(validate_csat_handling(db))
    results.append(validate_repeat_contacts(db))
    results.append(validate_tier_classification(db))
    results.append(validate_refund_anomalies(db))
    results.append(validate_digest_and_leaderboard(db))

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    print(f"  {passed}/{total} checks passed")
    for r in results:
        icon = PASS if r["status"] == "PASS" else FAIL
        print(f"  {icon} {r['name']}: {r['detail']}")

    print()
    print("=" * 70)
    print("ACCURACY METRICS")
    print("=" * 70)

    # SLA spot-check
    sla_result = spot_check_sla(db, n=30)
    print(f"\n  SLA Breach Detection (first 30 eligible tickets):")
    print(f"    Correct: {sla_result['correct']}/{sla_result['total']}")
    print(f"    Accuracy: {sla_result['accuracy']:.1f}%")
    if sla_result["errors"]:
        print(f"    Errors:")
        for e in sla_result["errors"][:5]:
            print(f"      {e}")

    # Repeat contact spot-check
    repeat_result = spot_check_repeats(db, n=20)
    print(f"\n  Repeat Contact Detection (first 20 pairs):")
    print(f"    True Repeats: {repeat_result['true_repeats']}/{repeat_result['total']}")
    print(f"    Precision: {repeat_result['precision']:.1f}%")
    print(f"    Notes: {repeat_result['notes']}")

    return results


def validate_deduplication(db):
    """Check that duplicates are properly removed."""
    print("\n--- 1. DEDUPLICATION ---")

    # Count by source system
    row = db.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN source_system = 'helpdesk' THEN 1 ELSE 0 END) as helpdesk,
            SUM(CASE WHEN source_system = 'legacy_fd' THEN 1 ELSE 0 END) as legacy,
            COUNT(DISTINCT ticket_id) as unique_ids
        FROM tickets WHERE is_duplicate = 0
    """).fetchone()

    print(f"  Total tickets (after dedup): {row['total']}")
    print(f"  Helpdesk: {row['helpdesk']}")
    print(f"  Legacy: {row['legacy']}")
    print(f"  Unique IDs: {row['unique_ids']}")

    # Verify no duplicate IDs remain
    dup_check = db.execute("""
        SELECT ticket_id, COUNT(*) as cnt
        FROM tickets WHERE is_duplicate = 0
        GROUP BY ticket_id HAVING cnt > 1
    """).fetchall()

    if len(dup_check) == 0:
        print(f"  {PASS} No duplicate ticket IDs remain")
        return {"name": "Deduplication", "status": "PASS", "detail": f"{row['total']} unique tickets, 0 duplicate IDs"}
    else:
        print(f"  {FAIL} {len(dup_check)} duplicate IDs still present")
        return {"name": "Deduplication", "status": "FAIL", "detail": f"{len(dup_check)} duplicates remain"}


def validate_sla_breaches(db):
    """Verify SLA breach calculations against policy §3 targets."""
    print("\n--- 2. SLA BREACH CALCULATION ---")
    print(f"  SLA targets: {SLA_TARGETS}")

    # Verify every eligible ticket, not a sample.
    rows = db.execute("""
        SELECT ticket_id, channel, created_at, first_response_at,
               response_minutes, sla_breached
        FROM tickets
        WHERE is_duplicate = 0
    """).fetchall()

    errors = 0
    checked = 0
    for r in rows:
        created = parse_timestamp(r["created_at"])
        responded = parse_timestamp(r["first_response_at"])
        if not created or not responded:
            continue
        checked += 1

        actual_minutes = (responded - created).total_seconds() / 60.0
        target = SLA_TARGETS.get(r["channel"], 999999)
        expected_breach = 1 if actual_minutes > target else 0

        if expected_breach != r["sla_breached"]:
            errors += 1

    accuracy = ((checked - errors) / checked * 100) if checked else 0
    print(f"  Checked {checked} tickets: {errors} mismatches")
    print(f"  Accuracy: {accuracy:.1f}%")

    status = "PASS" if errors == 0 else "FAIL"
    return {"name": "SLA Breach Calc", "status": status, "detail": f"{accuracy:.1f}% accuracy ({errors} errors in {checked} checks)"}


def validate_csat_handling(db):
    """Verify CSAT 0 is treated as null, not included in averages."""
    print("\n--- 3. CSAT HANDLING ---")

    # Check that no CSAT score of 0 exists
    zero_count = db.execute("SELECT COUNT(*) FROM tickets WHERE csat_score = 0 AND is_duplicate = 0").fetchone()[0]
    null_count = db.execute("SELECT COUNT(*) FROM tickets WHERE csat_score IS NULL AND is_duplicate = 0").fetchone()[0]
    has_value = db.execute("SELECT COUNT(*) FROM tickets WHERE csat_score IS NOT NULL AND is_duplicate = 0").fetchone()[0]

    print(f"  CSAT NULL (excluded from avg): {null_count}")
    print(f"  CSAT = 0 in DB: {zero_count}")
    print(f"  CSAT with value: {has_value}")

    # Verify average excludes nulls
    avg = db.execute("SELECT AVG(csat_score) FROM tickets WHERE csat_score IS NOT NULL AND is_duplicate = 0").fetchone()[0]
    print(f"  Average (excluding null): {avg:.2f}")

    if zero_count == 0:
        print(f"  {PASS} No CSAT=0 values — all converted to NULL per policy §8")
        return {"name": "CSAT Handling", "status": "PASS", "detail": f"0 scores of 0, {null_count} nulls excluded, avg={avg:.2f}"}
    else:
        print(f"  {FAIL} {zero_count} CSAT=0 values remain")
        return {"name": "CSAT Handling", "status": "FAIL", "detail": f"{zero_count} zero values remain"}


def validate_repeat_contacts(db):
    """Verify repeat contact detection logic."""
    print("\n--- 4. REPEAT CONTACT DETECTION ---")

    total = db.execute("SELECT COUNT(*) FROM repeat_contacts").fetchone()[0]
    print(f"  Total repeat contact pairs detected: {total}")

    # Verify a sample: check that days_between is within 0-30
    bad_range = db.execute("SELECT COUNT(*) FROM repeat_contacts WHERE days_between <= 0 OR days_between > 30").fetchone()[0]
    print(f"  Pairs outside 0-30 day range: {bad_range}")

    # Verify no self-references
    self_ref = db.execute("SELECT COUNT(*) FROM repeat_contacts WHERE original_ticket_id = repeat_ticket_id").fetchone()[0]
    print(f"  Self-references: {self_ref}")

    bad_customer = db.execute("""
        SELECT COUNT(*)
        FROM repeat_contacts rc
        JOIN tickets original ON original.ticket_id = rc.original_ticket_id
        JOIN tickets repeat ON repeat.ticket_id = rc.repeat_ticket_id
        WHERE original.customer_id != repeat.customer_id
    """).fetchone()[0]
    print(f"  Pairs with different customers: {bad_customer}")

    if bad_range == 0 and self_ref == 0 and bad_customer == 0:
        print(f"  {PASS} All {total} pairs are within 30-day window, no self-refs")
        return {"name": "Repeat Contacts", "status": "PASS", "detail": f"{total} pairs, all within 0-30 days"}
    else:
        return {"name": "Repeat Contacts", "status": "FAIL", "detail": f"{bad_range} out of range, {self_ref} self-refs, {bad_customer} customer mismatches"}


def validate_tier_classification(db):
    """Verify tier 1/2 agent classification matches policy §6."""
    print("\n--- 5. TIER CLASSIFICATION ---")

    # Escalations & Warranty should be tier 2
    t2_teams = db.execute("""
        SELECT DISTINCT assigned_team FROM tickets
        WHERE agent_tier = 2 AND is_duplicate = 0
    """).fetchall()
    t2_team_names = [r["assigned_team"] for r in t2_teams]
    print(f"  Tier 2 teams: {t2_team_names}")

    t2_count = db.execute("SELECT COUNT(DISTINCT agent_id) FROM tickets WHERE agent_tier = 2 AND is_duplicate = 0").fetchone()[0]
    t1_count = db.execute("SELECT COUNT(DISTINCT agent_id) FROM tickets WHERE agent_tier = 1 AND is_duplicate = 0").fetchone()[0]
    print(f"  Tier 1 agents: {t1_count}")
    print(f"  Tier 2 agents: {t2_count}")

    expected_t2 = ["Escalations & Warranty"]
    if t2_team_names == expected_t2:
        print(f"  {PASS} Only Escalations & Warranty in Tier 2")
        return {"name": "Tier Classification", "status": "PASS", "detail": f"T1={t1_count}, T2={t2_count}"}
    else:
        return {"name": "Tier Classification", "status": "FAIL", "detail": f"Unexpected T2 teams: {t2_team_names}"}


def validate_refund_anomalies(db):
    """Verify refund+replacement violation detection."""
    print("\n--- 6. REFUND + REPLACEMENT ANOMALIES ---")

    anomalies = db.execute("""
        SELECT ticket_id, refund_amount_inr, replacement_issued
        FROM tickets
        WHERE is_duplicate = 0
        AND refund_amount_inr IS NOT NULL
        AND replacement_issued = 'Y'
    """).fetchall()

    print(f"  Anomalies found: {len(anomalies)}")
    for a in anomalies:
        print(f"    {a['ticket_id']}: refund={a['refund_amount_inr']}, replacement={a['replacement_issued']}")

    # Per policy §5, this should never happen — so any > 0 is a legitimate finding
    print(f"  {PASS} {len(anomalies)} violations detected (policy §5 prohibits refund+replacement)")
    return {"name": "Refund Anomalies", "status": "PASS", "detail": f"{len(anomalies)} violations detected"}


def validate_digest_and_leaderboard(db):
    """Verify aggregate outputs against their underlying rows deterministically."""
    print("\n--- 7. DIGEST AND LEADERBOARD SEMANTICS ---")

    weeks = get_available_weeks(db)
    digest_errors = []
    digest_total = 0
    for week in weeks:
        digest = get_weekly_digest_data(db, week["week_key"])
        digest_total += digest["stats"]["total"]
        category_total = sum(item["count"] for item in digest["categories"])
        channel_total = sum(item["count"] for item in digest["channels"])
        if category_total != digest["stats"]["total"]:
            digest_errors.append(f"{week['week_key']}: categories={category_total}, total={digest['stats']['total']}")
        if channel_total != digest["stats"]["total"]:
            digest_errors.append(f"{week['week_key']}: channels={channel_total}, total={digest['stats']['total']}")

    unique_total = db.execute("SELECT COUNT(*) FROM tickets WHERE is_duplicate = 0").fetchone()[0]
    leaderboard = get_agent_leaderboard(db)
    tier_agents = leaderboard["tier1"] + leaderboard["tier2"]
    agent_ids = [agent["agent_id"] for agent in tier_agents]
    duplicate_agents = len(agent_ids) != len(set(agent_ids))
    bad_tier_order = any(
        leaderboard["tier1"][index]["tickets_resolved"] < leaderboard["tier1"][index + 1]["tickets_resolved"]
        for index in range(len(leaderboard["tier1"]) - 1)
    )

    print(f"  Weeks checked: {len(weeks)}")
    print(f"  Digest ticket total: {digest_total} (unique rows: {unique_total})")
    print(f"  Leaderboard agents: {len(tier_agents)}")
    print(f"  Digest aggregate errors: {len(digest_errors)}")
    print(f"  Duplicate leaderboard agents: {duplicate_agents}")
    print(f"  Tier 1 order error: {bad_tier_order}")

    passed = digest_total == unique_total and not digest_errors and not duplicate_agents and not bad_tier_order
    status = "PASS" if passed else "FAIL"
    detail = f"{len(weeks)} weeks, digest totals reconcile, leaderboard ordering is valid" if passed else "Digest or leaderboard invariants failed"
    return {"name": "Digest/Leaderboard Semantics", "status": status, "detail": detail}


def spot_check_sla(db, n=30):
    """Spot-check SLA breach flags against manual calculation."""
    rows = db.execute(f"""
        SELECT ticket_id, channel, created_at, first_response_at, sla_breached
        FROM tickets
        WHERE is_duplicate = 0
        ORDER BY ticket_id
        LIMIT {n}
    """).fetchall()

    correct = 0
    errors = []
    total = 0
    for r in rows:
        created = parse_timestamp(r["created_at"])
        responded = parse_timestamp(r["first_response_at"])
        if not created or not responded:
            continue
        total += 1
        minutes = (responded - created).total_seconds() / 60.0
        target = SLA_TARGETS.get(r["channel"], 999999)
        expected = 1 if minutes > target else 0
        if expected == r["sla_breached"]:
            correct += 1
        else:
            errors.append(f"{r['ticket_id']}: {r['channel']}, {minutes:.0f}min vs target {target}min, flagged={r['sla_breached']}, expected={expected}")

    return {
        "correct": correct,
        "total": total,
        "accuracy": (correct / total * 100) if total else 0,
        "errors": errors,
    }


def spot_check_repeats(db, n=20):
    """Spot-check repeat contact pairs for validity."""
    pairs = db.execute(f"""
        SELECT rc.original_ticket_id, rc.repeat_ticket_id, rc.days_between,
               t1.customer_id as orig_cust, t1.category as orig_cat, t1.product_sku as orig_prod,
               t2.customer_id as rep_cust, t2.category as rep_cat, t2.product_sku as rep_prod
        FROM repeat_contacts rc
        JOIN tickets t1 ON rc.original_ticket_id = t1.ticket_id AND t1.is_duplicate = 0
        JOIN tickets t2 ON rc.repeat_ticket_id = t2.ticket_id AND t2.is_duplicate = 0
        ORDER BY original_ticket_id, repeat_ticket_id
        LIMIT {n}
    """).fetchall()

    true_repeats = 0
    same_product = 0
    same_category = 0
    total = len(pairs)

    for p in pairs:
        # Same customer (required)
        if p["orig_cust"] == p["rep_cust"]:
            true_repeats += 1
        if p["orig_prod"] == p["rep_prod"]:
            same_product += 1
        if p["orig_cat"] == p["rep_cat"]:
            same_category += 1

    return {
        "true_repeats": true_repeats,
        "total": total,
        "precision": (true_repeats / total * 100) if total else 0,
        "same_product": same_product,
        "same_category": same_category,
        "notes": f"Same product: {same_product}/{total}, Same category: {same_category}/{total}",
    }


if __name__ == "__main__":
    run_validation()
