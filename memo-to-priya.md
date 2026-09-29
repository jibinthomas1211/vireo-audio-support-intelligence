# Memo: Vireo Audio Support Intelligence

**To:** Priya Raman, Head of Customer Experience  
**From:** Kabir Nanda, Account Lead  
**Subject:** Weekly digest, leaderboard, and a repeat-contact problem worth investigating  
**Date:** 29 September 2026

## Decision

Use the tool weekly to target repeat contacts, with an operating goal of reducing the rate from the observed 32.6% to 25.0% within two quarters.

The supplied 18-month export contains 11,875 deduplicated tickets and 3,871 detected repeat contacts. At the policy's blended cost of Rs 290 per contact (per your correction to Arjun), reaching 25.0% at the current run rate would avoid approximately 150 contacts per quarter, worth about **Rs 43,500 per quarter**. This is an operating target, not a claim that every repeat contact is preventable.

## What the data shows

The first finding worth acting on: **Delivery & Shipping generates the most repeat contacts (780)**, followed by Billing & Payments (621). By product, the **Pulse 2 True Wireless Earbuds alone account for 1,082 repeat contacts** — nearly 28% of all repeats from a single SKU.

Neha flagged that chat frontline agents hear "I already told your colleague this." The data confirms it: **1,714 of the 3,871 repeat contacts originated on the chat channel** (33.2% repeat rate), making chat the single largest contributor. This is where the first intervention should focus.

Four tickets were flagged with both a refund and a replacement issued on the same case — a policy §5 violation that warrants review.

## What the tool provides

- A **weekly digest** of complaint categories, products, channels, SLA breaches, refunds, CSAT, and repeat contacts — exactly the reading tool you asked for.
- A **frontline leaderboard** by tickets resolved, as requested.
- A **separate Escalations & Warranty view** ranked by CSAT and resolution quality rather than ticket volume, per Neha's note that warranty cases take days by design.
- **Trend views** for repeat contacts and SLA breaches over time.
- **Anomaly flags** for refund-plus-replacement violations, inter-team transfers, and SLA credits exposure (1,051 breaches × Rs 350 = Rs 3.7 lakh).

## Recommendation

Start with Delivery & Shipping repeat contacts on the chat channel. Assign one owner, inspect the closing notes on the first 20 cases, and record the action taken. Review the following week's repeat-contact rate and category mix to see whether the intervention worked.

Keep the leaderboard as a coaching and workload signal. It should not be used to compare warranty or escalation work directly with frontline volume because those cases are intentionally multi-touch.

## Reliability and limits

The current validation report passes **7/7 checks**: all 11,875 SLA calculations verified at 100% accuracy, all 3,871 repeat-contact pairs within the 0–30 day window with no self-references, deduplication clean (653 Freshdesk migration duplicates removed per Sameer's warning), CSAT 0-values excluded per policy §8, tier classification correct, all 80 weekly digest totals reconciled, and leaderboard ordering valid.

Repeat contacts are inferred from the same customer opening another ticket within 30 days of resolution. The result is a useful prioritisation signal, not a confirmed root-cause label. The digest's AI narrative is optional and costs nothing by default; without a Gemini key, the tool uses a transparent rule-based summary — no surprise model bills in November.

## Next steps

1. Assign an owner for Delivery & Shipping repeat contacts on chat — the single largest pocket of avoidable cost.
2. Review the Pulse 2 product for recurring themes in customer messages and closing notes.
3. Reassess the 25.0% target after two quarters using the same definitions.

