# AI Usage Disclosure

## Tools used

- GitHub Copilot in VS Code for repository inspection, implementation, documentation, and test execution.
- Python, SQLite, FastAPI, React, Vite, and Recharts for the tool itself.
- Google Gemini through the `google-genai` SDK for optional weekly narrative generation.
- A rule-based Python fallback when no Gemini key is configured or an API call fails.

## Model and cost

The configured model is `gemini-3.5-flash-lite`, selected through `GEMINI_MODEL`. No Gemini API cost is included in this submission because the delivered workflow works without a key and uses the local rule-based fallback by default. If a key is enabled, the account owner should verify current Google pricing and set a usage budget before running it against production data.

## Prompts used

The weekly prompt asks the model to act as a Vireo Audio support analyst and produce five sections: Executive Summary, Top Complaint Themes, Product Spotlight, Operational Flags, and Recommended Actions. It supplies aggregated weekly statistics, category and product summaries, and up to 60 truncated customer opening messages. The requested output is under 400 words and must use the actual week data.

The implementation prompt is in `backend/ai_digest.py`; no customer message is sent outside the optional Gemini request path.

## What was changed between versions

- Added source-system deduplication, keeping the helpdesk copy when a ticket ID appears in both systems.
- Converted CSAT `0` to no-response/null before calculating averages.
- Added the documented legacy timestamp correction and retained a flag for affected rows.
- Added repeat-contact detection, SLA calculations, tier-aware leaderboard logic, and policy anomaly flags.
- Added deterministic validation for all loaded records and weekly aggregate semantics.
- Added a rule-based fallback so the tool does not depend on an API key.

## What was discarded

- A platform-style workflow was left out because Priya asked for a simple reading tool.
- Warranty and Escalations were not ranked by ticket count because the email thread and policy state that this work is multi-touch by design.
- No per-ticket AI classification pipeline was added; it would add cost and complexity without being necessary for the weekly digest.
- Unused Vite/React starter assets were removed from the final frontend.
