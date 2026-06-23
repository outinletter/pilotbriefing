from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import OpsIntelItem, OpsIntelRun
from ..services.official_event_parsers import collect_recent_official_events
from ..services.ops_intel_collector import collect_once, refine_official_items
from ..services.report_generator import write_daily_briefing, write_review
from ..services.telegram_sender import send_telegram_message, telegram_message

router = APIRouter()


@router.get("/api/ops-intel/status")
def ops_intel_status(db: Session = Depends(get_db)):
    last_run = db.query(OpsIntelRun).order_by(OpsIntelRun.started_at.desc()).first()
    item_count = db.query(OpsIntelItem).count()
    return {
        "items_in_database": item_count,
        "autostart": settings.ops_intel_autostart,
        "interval_hours": settings.ops_intel_interval_hours,
        "last_run": {
            "status": last_run.status,
            "started_at": last_run.started_at,
            "finished_at": last_run.finished_at,
            "items_checked": last_run.items_checked,
            "items_saved": last_run.items_saved,
            "error": last_run.error,
        } if last_run else None,
    }


@router.post("/api/ops-intel/collect")
async def collect_ops_intel():
    return await collect_once()


@router.post("/api/ops-intel/collect-official-recent")
async def collect_official_recent_ops_intel():
    return await collect_recent_official_events(years_back=7)


@router.get("/api/ops-intel/items")
def ops_intel_items(db: Session = Depends(get_db)):
    rows = db.query(OpsIntelItem).order_by(OpsIntelItem.updated_at.desc()).limit(50).all()
    return [
        {
            "source_name": row.source_name,
            "source_url": row.source_url,
            "title": row.title,
            "category": row.category,
            "severity": row.severity,
            "summary": row.summary,
            "operational_lesson": row.operational_lesson,
            "a350_b787_applicability": row.a350_b787_applicability,
            "recommended_action": row.recommended_action,
            "tags": row.tags,
            "last_status": row.last_status,
            "last_checked_at": row.last_checked_at,
        }
        for row in rows
    ]


@router.post("/api/ops-intel/refine-official")
def refine_official_report_items():
    return refine_official_items()


@router.post("/api/ops-intel/reports/daily")
def generate_daily_report(db: Session = Depends(get_db)):
    return write_daily_briefing(db)


@router.post("/api/ops-intel/reports/weekly")
def generate_weekly_report(db: Session = Depends(get_db)):
    return write_review(db, "weekly")


@router.post("/api/ops-intel/reports/monthly")
def generate_monthly_report(db: Session = Depends(get_db)):
    return write_review(db, "monthly")


@router.get("/api/ops-intel/telegram/message")
def preview_telegram_message(db: Session = Depends(get_db)):
    return {"message": telegram_message(db)}


@router.post("/api/ops-intel/telegram/send")
async def send_ops_intel_telegram(db: Session = Depends(get_db)):
    return await send_telegram_message(db)
