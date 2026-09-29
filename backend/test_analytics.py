"""Quick test of analytics functions."""
from data_loader import init_database
from analytics import get_agent_leaderboard, get_available_weeks, get_insights
import json

db = init_database()

# Test weeks
weeks = get_available_weeks(db)
print(f"Total weeks: {len(weeks)}")
print(f"First: {weeks[0]}")
print(f"Last: {weeks[-1]}")

# Test leaderboard
lb = get_agent_leaderboard(db, week_key="2026-W10")
print(f"\nTier1 agents: {len(lb['tier1'])}")
print(f"Tier2 agents: {len(lb['tier2'])}")
if lb["tier1"]:
    print(f"Top T1: {lb['tier1'][0]['name']} - {lb['tier1'][0]['tickets_resolved']} tickets")
if lb["tier2"]:
    print(f"Top T2: {lb['tier2'][0]['name']} - CSAT {lb['tier2'][0]['avg_csat']}")

# Test insights
ins = get_insights(db)
print(f"\nRepeat trend points: {len(ins['repeat_contact_trend'])}")
print(f"SLA trend points: {len(ins['sla_breach_trend'])}")
print(f"Refund anomalies: {len(ins['refund_replacement_anomalies'])}")
print(f"Categories: {len(ins['category_insights'])}")

# Show a sample digest week
from analytics import get_weekly_digest_data
digest = get_weekly_digest_data(db, "2026-W10")
print(f"\nDigest week 2026-W10: {digest['stats']['total']} tickets")
print(f"Categories: {len(digest['categories'])}")
print(f"Messages sampled: {len(digest['sample_messages'])}")

print("\nAll tests passed!")
