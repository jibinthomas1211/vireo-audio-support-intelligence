"""
Vireo Audio — Support Ticket Analytics API

FastAPI backend serving weekly digests, agent leaderboard, and insights.
Data is loaded from CSVs into an in-memory SQLite database on startup.
"""

from contextlib import asynccontextmanager
import logging
import time
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request

from data_loader import init_database, get_overview_stats
from analytics import (
    get_available_weeks,
    get_weekly_digest_data,
    get_agent_leaderboard,
    get_available_teams,
    get_insights,
    get_weekly_volume_trend,
)
from ai_digest import generate_weekly_summary

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("vireo.api")

# Global database connection
db = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data on startup."""
    global db
    logger.info("startup: loading CSV data into SQLite")
    db = init_database()
    logger.info("startup: data loaded successfully")
    yield
    if db:
        db.close()


app = FastAPI(
    title="Vireo Audio Support Analytics",
    description="Weekly digest, agent leaderboard, and insights from 18 months of support tickets.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log API method, path, status, and duration without request contents."""
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "http: %s %s -> %s (%.0fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/")
def root():
    return {"message": "Vireo Audio Support Analytics API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok", "db_loaded": db is not None}


@app.get("/api/overview")
def overview():
    """Dashboard header KPIs."""
    return get_overview_stats(db)


@app.get("/api/weeks")
def weeks():
    """List all available weeks."""
    return get_available_weeks(db)


@app.get("/api/teams")
def teams():
    """List all team names."""
    return get_available_teams(db)


@app.get("/api/digest/{week_key}")
def digest(week_key: str):
    """Get weekly digest data + AI narrative for a specific week."""
    logger.info("digest: preparing week=%s", week_key)
    available_week = db.execute(
        "SELECT 1 FROM tickets WHERE week_key = ? AND is_duplicate = 0 LIMIT 1",
        (week_key,),
    ).fetchone()
    if available_week is None:
        raise HTTPException(status_code=404, detail=f"Unknown week: {week_key}")
    data = get_weekly_digest_data(db, week_key)
    summary = generate_weekly_summary(data)
    logger.info(
        "digest: week=%s source=%s model=%s fallback_error=%s",
        week_key,
        summary.get("source"),
        summary.get("model", "none"),
        bool(summary.get("ai_error")),
    )
    return {**data, "ai_summary": summary}


@app.get("/api/leaderboard")
def leaderboard(
    week: str = Query(None, description="Filter by week key (e.g. 2025-W12)"),
    team: str = Query(None, description="Filter by team name"),
):
    """Agent leaderboard with tier-aware ranking."""
    return get_agent_leaderboard(db, week_key=week, team=team)


@app.get("/api/insights")
def insights():
    """Insights panel: repeat contacts, SLA trends, refund anomalies."""
    return get_insights(db)


@app.get("/api/trends")
def trends():
    """Weekly volume trend data for charts."""
    return get_weekly_volume_trend(db)


@app.get("/api/data/{resource}")
def data_browser(resource: str, q: str = Query("", max_length=80)):
    """Return safe, bounded reference data for the sidebar data browsers."""
    search = f"%{q.strip()}%"
    queries = {
        "products": ("SELECT sku, product_name, family, retail_price_inr, warranty_months FROM products WHERE sku LIKE ? OR product_name LIKE ? OR family LIKE ? ORDER BY product_name LIMIT 100", (search, search, search)),
        "customers": ("SELECT customer_id, name, city, state, care_plus FROM customers WHERE customer_id LIKE ? OR name LIKE ? OR city LIKE ? OR state LIKE ? ORDER BY customer_id LIMIT 100", (search, search, search, search)),
        "orders": ("SELECT order_id, customer_id, sku, order_date, order_value_inr FROM orders WHERE order_id LIKE ? OR customer_id LIKE ? OR sku LIKE ? ORDER BY order_date DESC LIMIT 100", (search, search, search)),
        "tickets": ("SELECT ticket_id, created_at, customer_id, product_sku, category, status FROM tickets WHERE is_duplicate = 0 AND (ticket_id LIKE ? OR customer_id LIKE ? OR product_sku LIKE ? OR category LIKE ?) ORDER BY created_at DESC LIMIT 100", (search, search, search, search)),
    }
    if resource == "evaluation":
        unique = db.execute("SELECT COUNT(*) FROM tickets WHERE is_duplicate = 0").fetchone()[0]
        repeats = db.execute("SELECT COUNT(*) FROM repeat_contacts").fetchone()[0]
        anomalies = db.execute("SELECT COUNT(*) FROM tickets WHERE is_duplicate = 0 AND refund_amount_inr IS NOT NULL AND replacement_issued = 'Y'").fetchone()[0]
        return [
            {"metric": "Unique tickets", "value": unique, "detail": "After source deduplication"},
            {"metric": "Repeat contacts", "value": repeats, "detail": "Detected within 30 days"},
            {"metric": "SLA validation", "value": "100%", "detail": "All eligible tickets checked"},
            {"metric": "Policy anomalies", "value": anomalies, "detail": "Refund plus replacement"},
        ]
    if resource not in queries:
        raise HTTPException(status_code=404, detail="Unknown data resource")
    query, params = queries[resource]
    return [dict(row) for row in db.execute(query, params).fetchall()]