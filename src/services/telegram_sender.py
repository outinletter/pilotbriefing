import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import OpsIntelItem
from .report_generator import clean_summary, top_items


def telegram_message(db: Session) -> str:
    items = top_items(db, limit=3)
    if not items:
        return "[121/135 OPS INTEL]\n\nNo operational-intelligence items are currently stored."
    lines = ["[121/135 OPS INTEL]", ""]
    for index, item in enumerate(items, start=1):
        lines.extend([
            f"{index}. Severity: {item.severity or 'Low'}",
            f"Category: {item.category or 'Unclassified'}",
            f"Aircraft: A350/B787 screen",
            f"Event: {item.title or 'Untitled item'}",
            "",
            "Summary:",
            clean_summary(item.summary, 320),
            "",
            "Operational Lesson:",
            clean_summary(item.operational_lesson, 220),
            "",
            "A350/B787 Relevance:",
            clean_summary(item.a350_b787_applicability, 220),
            "",
            "Action:",
            clean_summary(item.recommended_action, 220),
            "",
        ])
    return "\n".join(lines).strip()


async def send_telegram_message(db: Session) -> dict:
    message = telegram_message(db)
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return {"sent": False, "reason": "telegram_not_configured", "message": message}
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": settings.telegram_chat_id, "text": message, "disable_web_page_preview": True}
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
    return {"sent": True, "message": message}
