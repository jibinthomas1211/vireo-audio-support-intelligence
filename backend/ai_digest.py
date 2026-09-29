"""
ai_digest.py — AI-powered weekly digest generation using Google Gemini.

Generates human-readable narrative summaries of weekly support ticket data.
Falls back to rule-based summarization if no API key is configured.
"""

import os
import json
import logging
from google import genai
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("vireo.gemini")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def _get_client():
    """Get Gemini client if API key is available."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def generate_weekly_summary(digest_data: dict) -> dict:
    """
    Generate an AI summary of the week's support activity.
    Returns a dict with narrative sections.
    """
    client = _get_client()
    if client:
        logger.info("gemini: request started week=%s model=%s", digest_data["week_key"], GEMINI_MODEL)
        return _ai_summary(client, digest_data)
    else:
        logger.info("gemini: API key not configured; using rule-based summary week=%s", digest_data["week_key"])
        return _rule_based_summary(digest_data)


def _ai_summary(client, digest_data: dict) -> dict:
    """Use Gemini to generate a narrative summary."""

    stats = digest_data["stats"]
    categories = digest_data["categories"]
    products = digest_data["products"]
    messages = digest_data["sample_messages"]

    # Build the prompt
    message_texts = "\n".join(
        f"- [{m['category']}][{m['product']}] {m['message'][:200]}"
        for m in messages[:60]
    )

    category_summary = "\n".join(
        f"- {c['name']}: {c['count']} tickets, CSAT {c['avg_csat'] or 'N/A'}, {c['sla_breaches']} SLA breaches"
        for c in categories
    )

    product_summary = "\n".join(
        f"- {p['name'] or p['sku']}: {p['count']} tickets, CSAT {p['avg_csat'] or 'N/A'}"
        for p in products[:10]
    )

    prompt = f"""You are a support analytics analyst for Vireo Audio, a consumer electronics brand selling earbuds, headphones, speakers, and smartwatches in India.

Analyze the following weekly support data and produce a concise weekly digest.

WEEK: {digest_data['week_key']}

STATS:
- Total tickets: {stats['total']}
- Resolved: {stats['resolved']}
- SLA breaches: {stats['sla_breaches']} ({stats['sla_breach_rate']}%)
- Average CSAT: {stats['avg_csat'] or 'N/A'} / 5
- Average first response: {stats['avg_response_minutes'] or 'N/A'} minutes
- Refunds issued: Rs {stats['total_refunds']:,.0f}
- Replacements: {stats['replacements']}
- Repeat contacts: {stats['repeat_contacts']}

CATEGORIES:
{category_summary}

PRODUCTS:
{product_summary}

SAMPLE CUSTOMER MESSAGES:
{message_texts}

Write a digest with these exact sections:
1. **Executive Summary** (2-3 sentences covering the most important thing this week)
2. **Top Complaint Themes** (3-5 bullet points, each with a theme name, how many tickets roughly, and what customers are saying)
3. **Product Spotlight** (which products had issues and what kind)
4. **Operational Flags** (SLA breaches, repeat contact patterns, anything unusual)
5. **Recommended Actions** (2-3 concrete, actionable items)

Be specific, use the actual data. Write for a Head of Customer Experience who wants to know what happened this week. Keep the total under 400 words."""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        narrative = response.text
        logger.info("gemini: request succeeded week=%s output_chars=%s", digest_data["week_key"], len(narrative or ""))

        return {
            "source": "ai",
            "model": GEMINI_MODEL,
            "narrative": narrative,
            "week_key": digest_data["week_key"],
        }
    except Exception as e:
        # Fall back to rule-based if API fails
        logger.exception("gemini: request failed week=%s; using rule-based fallback", digest_data["week_key"])
        result = _rule_based_summary(digest_data)
        result["ai_error"] = str(e)
        return result


def _rule_based_summary(digest_data: dict) -> dict:
    """Generate a summary using rules when no API key is available."""

    stats = digest_data["stats"]
    categories = digest_data["categories"]
    products = digest_data["products"]

    # Executive summary
    total = stats["total"]
    resolved = stats["resolved"]
    csat = stats["avg_csat"]
    breaches = stats["sla_breaches"]
    breach_rate = stats["sla_breach_rate"]

    exec_summary = f"This week saw {total} support tickets"
    if resolved:
        exec_summary += f", of which {resolved} were resolved"
    exec_summary += "."
    if csat:
        exec_summary += f" Average CSAT was {csat}/5."
    if breaches:
        exec_summary += f" {breaches} tickets ({breach_rate}%) breached SLA targets."

    # Top categories
    top_cats = categories[:5]
    cat_bullets = []
    for c in top_cats:
        bullet = f"**{c['name']}**: {c['count']} tickets"
        if c["avg_csat"]:
            bullet += f" (CSAT {c['avg_csat']})"
        if c["sla_breaches"]:
            bullet += f" — {c['sla_breaches']} SLA breaches"
        cat_bullets.append(bullet)

    # Product spotlight
    top_products = products[:5]
    prod_bullets = []
    for p in top_products:
        name = p["name"] or p["sku"]
        bullet = f"**{name}**: {p['count']} tickets"
        if p["avg_csat"]:
            bullet += f" (CSAT {p['avg_csat']})"
        prod_bullets.append(bullet)

    # Operational flags
    flags = []
    if breach_rate and breach_rate > 10:
        flags.append(f"⚠️ SLA breach rate at {breach_rate}% — above 10% threshold")
    if stats["repeat_contacts"] and stats["repeat_contacts"] > 0:
        flags.append(f"🔄 {stats['repeat_contacts']} repeat contacts detected this week")
    if stats["total_transfers"] and stats["total_transfers"] > 0:
        flags.append(f"↔️ {stats['total_transfers']} inter-team transfers (Rs {stats['total_transfers'] * 305:,.0f} transfer cost)")

    # Recommended actions
    actions = []
    if breaches and breaches > 0:
        worst_channel = None
        for ch in digest_data.get("channels", []):
            if ch["sla_breaches"] and ch["sla_breaches"] > 0:
                if worst_channel is None or ch["sla_breaches"] > worst_channel["sla_breaches"]:
                    worst_channel = ch
        if worst_channel:
            actions.append(f"Review {worst_channel['name']} queue staffing — {worst_channel['sla_breaches']} SLA breaches this week")

    if top_cats:
        actions.append(f"Investigate '{top_cats[0]['name']}' — highest volume category with {top_cats[0]['count']} tickets")

    if stats["repeat_contacts"] and stats["repeat_contacts"] > 5:
        actions.append("Audit repeat contact cases — customers re-contacting within 30 days is costing Rs 290/contact")

    narrative = f"""## Executive Summary

{exec_summary}

## Top Complaint Themes

{chr(10).join('- ' + b for b in cat_bullets)}

## Product Spotlight

{chr(10).join('- ' + b for b in prod_bullets)}

## Operational Flags

{chr(10).join('- ' + f for f in flags) if flags else '- No major operational concerns this week.'}

## Recommended Actions

{chr(10).join('- ' + a for a in actions) if actions else '- Continue monitoring.'}
"""

    return {
        "source": "rule_based",
        "model": None,
        "narrative": narrative,
        "week_key": digest_data["week_key"],
    }
