from collections import Counter
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import BASE_DIR
from ..models import OpsIntelItem


SEVERITY_RANK = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
QUALITY_RANK = {"official_report_candidate": 3, "official_source": 2, "supplementary_source": 1, "needs_source_review": 0}


def clean_summary(value: str | None, limit: int = 420) -> str:
    text = " ".join((value or "").split())
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")


def top_items(db: Session, limit: int = 10) -> list[OpsIntelItem]:
    rows = db.query(OpsIntelItem).order_by(OpsIntelItem.updated_at.desc()).limit(100).all()
    return sorted(rows, key=lambda row: (quality_rank(row), SEVERITY_RANK.get(row.severity or "Low", 0), row.updated_at), reverse=True)[:limit]


def quality_rank(item: OpsIntelItem) -> int:
    tags = item.tags or ""
    for tag, rank in QUALITY_RANK.items():
        if tag in tags:
            return rank
    return 0


def recent_items(db: Session, limit: int = 100) -> list[OpsIntelItem]:
    return db.query(OpsIntelItem).order_by(OpsIntelItem.updated_at.desc()).limit(limit).all()


def daily_briefing_markdown(db: Session) -> str:
    items = top_items(db)
    categories = Counter(item.category or "Unclassified" for item in items)
    high_interest = [item for item in items if item.severity in {"Critical", "High", "Medium"}]
    official_reports = [item for item in items if "official_report_candidate" in (item.tags or "")]
    today = datetime.utcnow().strftime("%Y-%m-%d")
    lines = [
        "# Daily Part 121 / Part 135 Operations Intelligence Briefing",
        "",
        f"Date: {today} UTC",
        "",
        "## Executive Summary",
        "",
        f"- {len(items)} recent operational-intelligence items were reviewed from the local database.",
        f"- Main categories: {', '.join(f'{name} ({count})' for name, count in categories.most_common(4)) or 'none'}.",
        f"- {len(official_reports)} top item(s) are tagged as official report/event candidates.",
        f"- {len(high_interest)} items are currently Medium or higher and should be reviewed for briefing or training value.",
        "",
        "## Top Events",
        "",
    ]
    for index, item in enumerate(items, start=1):
        lines.extend([
            f"### {index}. {item.title or 'Untitled item'}",
            "",
            f"- Source: [{item.source_name}]({item.source_url})",
            f"- Severity: {item.severity or 'Low'}",
            f"- Category: {item.category or 'Unclassified'}",
            f"- Summary: {clean_summary(item.summary)}",
            f"- Operational Lesson: {clean_summary(item.operational_lesson, 300)}",
            f"- A350/B787 Relevance: {clean_summary(item.a350_b787_applicability, 260)}",
            f"- Recommended Action: {clean_summary(item.recommended_action, 260)}",
            "",
        ])
    regulatory = [item for item in items if item.category == "Regulation"]
    training = [item for item in items if item.category in {"Training", "Human Factors / CRM"}]
    widebody = [item for item in items if "A350" in (item.a350_b787_applicability or "") or "B787" in (item.a350_b787_applicability or "")]
    lines.extend([
        "## Regulatory Watch",
        "",
        *(f"- {item.title} ({item.source_name})" for item in regulatory[:5]),
        "" if regulatory else "- No high-priority regulatory items in the current top set.",
        "",
        "## Training Implications",
        "",
        *(f"- {item.title}: {clean_summary(item.recommended_action, 220)}" for item in training[:5]),
        "" if training else "- No dedicated training items in the current top set.",
        "",
        "## A350 / B787 Relevance",
        "",
        *(f"- {item.title}: {clean_summary(item.a350_b787_applicability, 220)}" for item in widebody[:5]),
        "" if widebody else "- No dedicated A350/B787 items in the current top set.",
        "",
        "## Recommended Pilot Briefing",
        "",
        "- Review new operational-intelligence items for direct impact on dispatch, MEL, ETOPS, fatigue, navigation integrity, and approach threats.",
        "- Treat unverified or supplementary-source material as briefing prompts, not confirmed causal findings.",
        "- Convert confirmed official-source lessons into recurrent training, SOP review, or route briefing updates.",
        "",
    ])
    return "\n".join(lines)


def write_daily_briefing(db: Session) -> dict:
    markdown = daily_briefing_markdown(db)
    output_dir = BASE_DIR / "reports" / "daily"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{datetime.utcnow().strftime('%Y-%m-%d')}.md"
    path.write_text(markdown, encoding="utf-8")
    return {"path": str(path), "markdown": markdown}


def review_markdown(db: Session, period: str) -> str:
    items = recent_items(db)
    top = sorted(items, key=lambda row: (quality_rank(row), SEVERITY_RANK.get(row.severity or "Low", 0), row.updated_at), reverse=True)[:10]
    categories = Counter(item.category or "Unclassified" for item in items)
    severities = Counter(item.severity or "Low" for item in items)
    sources = Counter(item.source_name or "Unknown" for item in items)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    title = "Weekly" if period == "weekly" else "Monthly"
    lines = [
        f"# {title} Part 121 / Part 135 Operations Intelligence Review",
        "",
        f"Date: {today} UTC",
        "",
        "## Executive Summary",
        "",
        f"- {len(items)} stored operational-intelligence items were reviewed.",
        f"- Most frequent categories: {', '.join(f'{name} ({count})' for name, count in categories.most_common(5)) or 'none'}.",
        f"- Severity mix: {', '.join(f'{name} ({count})' for name, count in severities.most_common()) or 'none'}.",
        f"- Official report/event candidates: {sum(1 for item in items if 'official_report_candidate' in (item.tags or ''))}.",
        "",
        "## Top 10 Events",
        "",
    ]
    for index, item in enumerate(top, start=1):
        lines.extend([
            f"{index}. {item.title or 'Untitled item'}",
            f"   - Source: {item.source_name}",
            f"   - Category: {item.category or 'Unclassified'}",
            f"   - Severity: {item.severity or 'Low'}",
            f"   - Lesson: {clean_summary(item.operational_lesson, 260)}",
            f"   - Action: {clean_summary(item.recommended_action, 220)}",
            "",
        ])
    lines.extend([
        "## Recurring Patterns",
        "",
        *(f"- {name}: {count} item(s)" for name, count in categories.most_common(6)),
        "",
        "## Major Sources",
        "",
        *(f"- {name}: {count} item(s)" for name, count in sources.most_common(6)),
        "",
        "## A350 / B787 Implications",
        "",
        "- Review all Medium or higher items for ETOPS, dispatch release, MEL/CDL, fatigue, navigation integrity, and approach-threat relevance.",
        "- Convert official-source lessons into route briefing notes and recurrent training discussion points.",
        "",
        "## Training Recommendations",
        "",
        "- Add repeated categories to recurrent training discussion scenarios.",
        "- Use official-source items for SOP or briefing guide review.",
        "- Treat supplementary-source items as prompts until confirmed by official documents.",
        "",
    ])
    if period == "weekly":
        lines.extend([
            "## Weekly Review Questions",
            "",
            "1. What was the most important operational risk this week?",
            "2. Which area had more significant events, Part 121 or Part 135?",
            "3. What lessons apply to long-haul widebody operations?",
            "4. What should be reflected in the training program?",
            "5. What should be reflected in SOPs or briefing guides?",
            "",
        ])
    else:
        lines.extend([
            "## Monthly Management Review",
            "",
            "- Top 10 events are listed above for safety/training review.",
            "- Regulatory, human factors, technical reliability, and A350/B787 implications should be reviewed by category trend.",
            "- Training recommendations should be assigned to recurrent training, command upgrade, or route briefing owners.",
            "",
        ])
    return "\n".join(lines)


def write_review(db: Session, period: str) -> dict:
    markdown = review_markdown(db, period)
    output_dir = BASE_DIR / "reports" / period
    output_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.utcnow().strftime("%Y-%m-%d")
    path = output_dir / f"{date}.md"
    path.write_text(markdown, encoding="utf-8")
    return {"path": str(path), "markdown": markdown}
