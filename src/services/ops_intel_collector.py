import asyncio
import json
import re
from datetime import datetime
from html import unescape
from urllib.parse import urljoin, urlparse

import httpx

from ..config import BASE_DIR, settings
from ..database import SessionLocal
from ..models import OpsIntelItem, OpsIntelRun
from .official_event_parsers import collect_recent_official_events

_task: asyncio.Task | None = None
OFFICIAL_HOSTS = ["faa.gov", "ntsb.gov", "nasa.gov", "icao.int", "easa.europa.eu"]
EVENT_KEYWORDS = [
    "accident", "incident", "investigation", "safety", "recommendation", "safo", "info",
    "advisory", "airworthiness", "directive", "etops", "diversion", "fatigue", "crm",
    "runway", "unstable", "engine", "fire", "smoke", "gps", "gnss", "jamming", "spoofing",
    "mel", "dispatch", "training", "part-121", "part 121", "part-135", "part 135",
]
REPORT_KEYWORDS = [
    "report", "final", "preliminary", "investigation", "recommendation", "safo", "info",
    "advisory circular", "airworthiness directive", "directive", "safety alert",
    "accident", "incident", "asrs", "callback", "lessons learned",
]
SKIP_LABELS = ["skip to", "main content", "enable javascript", "subscribe", "login", "sign in", "privacy", "contact"]
MAX_EVENT_DETAIL_FETCHES_PER_SOURCE = 4


def load_sources() -> list[dict]:
    with open(BASE_DIR / "data" / "sources.json", encoding="utf-8") as f:
        return json.load(f)


def html_title(text: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def extract_main_text(html: str, limit: int = 1400) -> str:
    text = re.sub(r"(?is)<(script|style|nav|footer|header).*?>.*?</\1>", " ", html)
    text = clean_text(text)
    return text[:limit]


def is_same_site(base_url: str, url: str) -> bool:
    return urlparse(base_url).netloc == urlparse(url).netloc


def is_official_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host.endswith(domain) for domain in OFFICIAL_HOSTS)


def classify_title(title: str, source: dict) -> tuple[str, str]:
    text = title.lower()
    if any(word in text for word in ["accident", "incident", "investigation", "runway", "engine", "fire", "smoke"]):
        return "Accident / Incident", "Medium"
    if any(word in text for word in ["regulation", "advisory", "directive", "safo", "info", "airworthiness"]):
        return "Regulation", "Medium"
    if any(word in text for word in ["fatigue", "crm", "human factors"]):
        return "Human Factors / CRM", "Medium"
    if any(word in text for word in ["gps", "gnss", "jamming", "spoofing", "security"]):
        return "Security / External Threat", "High"
    if any(word in text for word in ["etops", "dispatch", "diversion", "fuel", "mel"]):
        return "Flight Operations", "Medium"
    return source["category"], "Low"


def quality_status(source: dict, status_code: int) -> str:
    if status_code >= 400:
        return "needs_source_review"
    if is_official_url(source["url"]):
        return "official_source"
    return "supplementary_source"


def candidate_quality(source: dict, url: str, title: str, text: str, status_code: int) -> str:
    if status_code >= 400:
        return "needs_source_review"
    if not is_official_url(url):
        return "supplementary_source"
    haystack = f"{title} {url} {text[:800]}".lower()
    if any(keyword in haystack for keyword in REPORT_KEYWORDS):
        return "official_report_candidate"
    return "official_source"


def detail_summary(source: dict, title: str, text: str, status_code: int) -> str:
    status = quality_status(source, status_code)
    if not text:
        return f"Collected event candidate from {source['name']}: {title}. Detail page text was not available. Quality status: {status}."
    return f"{title}. Source: {source['name']}. Quality status: {status}. Extract: {text}"


def detail_operational_lesson(category: str, title: str) -> str:
    if category == "Accident / Incident":
        return f"Use this item to brief event precursors, crew decision gates, and procedural defenses. Do not infer cause or fault until official findings confirm them."
    if category == "Regulation":
        return f"Check whether this item changes SOP, training, dispatch release, maintenance control, or compliance monitoring."
    if category == "Security / External Threat":
        return f"Review threat recognition, reporting, navigation cross-checks, and dispatch coordination for routes exposed to this threat."
    return f"Review this item for practical briefing value, training implications, and long-haul widebody operational relevance."


def extract_event_links(html: str, source: dict, limit: int = 8) -> list[dict]:
    links = []
    seen = set()
    for match in re.finditer(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL):
        href, label_html = match.groups()
        url = urljoin(source["url"], href)
        if not url.startswith("http") or not is_same_site(source["url"], url) or url in seen:
            continue
        label = clean_text(label_html)
        haystack = f"{label} {url}".lower()
        if (
            len(label) < 8
            or any(skip in haystack for skip in SKIP_LABELS)
            or not any(keyword in haystack for keyword in EVENT_KEYWORDS)
        ):
            continue
        category, severity = classify_title(label, source)
        links.append({"url": url, "title": label[:240], "category": category, "severity": severity})
        seen.add(url)
        if len(links) >= limit:
            break
    return links


def item_summary(source: dict, status_code: int, title: str) -> str:
    return f"Periodic source check saved for {source['name']}. HTTP status {status_code}. Latest page title: {title or 'not available'}."


def operational_lesson(source: dict) -> str:
    return f"Review new {source['category']} material from {source['name']} for procedure, training, dispatch, or safety-management relevance before using it in pilot briefings."


def recommended_action(source: dict) -> str:
    if source["category"] == "Regulation":
        return "Screen for regulatory or procedural changes and assign SOP/training review if applicable."
    if source["category"] == "Accident / Incident":
        return "Check for new factual reports, classify severity, and extract operational lessons without assigning blame."
    if source["category"] == "Human Factors / CRM":
        return "Review for recurrent training, fatigue, CRM, and decision-making discussion points."
    return "Review source updates and convert relevant items into the operational lessons database."


def upsert_item(db, source: dict, url: str, title: str, category: str, severity: str, status_code: int, summary: str, extra_tags: list[str] | None = None) -> bool:
    item = db.query(OpsIntelItem).filter(OpsIntelItem.source_url == url).first()
    created = False
    if not item:
        item = OpsIntelItem(source_name=source["name"], source_url=url)
        db.add(item)
        created = True
    item.title = title or source["name"]
    item.category = category
    item.severity = severity
    item.summary = summary
    item.operational_lesson = operational_lesson({"name": source["name"], "category": category})
    item.a350_b787_applicability = "Screen for relevance to A350/B787 long-haul operations, especially ETOPS, fatigue, dispatch, MEL, navigation, and approach threats."
    item.recommended_action = recommended_action({"category": category})
    item.tags = json.dumps(list(dict.fromkeys([*source.get("tags", []), category, severity, *(extra_tags or [])])))
    item.last_status = status_code
    item.last_checked_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    return created


async def fetch_source(client: httpx.AsyncClient, source: dict) -> dict:
    response = await client.get(source["url"])
    links = extract_event_links(response.text, source)
    enriched_links = []
    for link in links[:MAX_EVENT_DETAIL_FETCHES_PER_SOURCE]:
        try:
            detail_response = await client.get(link["url"])
            text = extract_main_text(detail_response.text)
            category, severity = classify_title(f"{link['title']} {text[:500]}", source)
            enriched_links.append({
                **link,
                "category": category,
                "severity": severity,
                "detail_status": detail_response.status_code,
                "detail_text": text,
            })
        except Exception:
            enriched_links.append({**link, "detail_status": response.status_code, "detail_text": ""})
    enriched_links.extend(links[MAX_EVENT_DETAIL_FETCHES_PER_SOURCE:])
    return {
        "source": source,
        "status_code": response.status_code,
        "title": html_title(response.text),
        "links": enriched_links,
    }


async def collect_once() -> dict:
    sources = load_sources()
    db = SessionLocal()
    run = OpsIntelRun()
    db.add(run)
    db.commit()
    saved = 0
    seen_urls = set()
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True, headers={"User-Agent": "OpsBriefing/0.1"}) as client:
            results = await asyncio.gather(*(fetch_source(client, source) for source in sources), return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                continue
            source = result["source"]
            if source["url"] in seen_urls:
                continue
            seen_urls.add(source["url"])
            if upsert_item(
                db,
                source,
                source["url"],
                result["title"] or source["name"],
                source["category"],
                "Low",
                result["status_code"],
                item_summary(source, result["status_code"], result["title"]),
            ):
                saved += 1
            for link in result["links"]:
                if link["url"] in seen_urls:
                    continue
                seen_urls.add(link["url"])
                summary = f"Collected event candidate from {source['name']}: {link['title']}."
                quality = candidate_quality(source, link["url"], link["title"], link.get("detail_text", ""), link.get("detail_status", result["status_code"]))
                if "detail_text" in link:
                    summary = detail_summary(source, link["title"], link.get("detail_text", ""), link.get("detail_status", result["status_code"]))
                if upsert_item(
                    db,
                    source,
                    link["url"],
                    link["title"],
                    link["category"],
                    link["severity"],
                    link.get("detail_status", result["status_code"]),
                    summary,
                    [quality],
                ):
                    saved += 1
                item = db.query(OpsIntelItem).filter(OpsIntelItem.source_url == link["url"]).first()
                if item and "detail_text" in link:
                    item.operational_lesson = detail_operational_lesson(link["category"], link["title"])
                    tags = json.loads(item.tags or "[]")
                    tags.append(quality)
                    item.tags = json.dumps(list(dict.fromkeys(tags)))
        db.commit()
        official_result = await collect_recent_official_events()
        saved += official_result.get("items_saved", 0)
        run.status = "complete"
        run.items_checked = len(sources) + official_result.get("items_checked", 0)
        run.items_saved = saved
        run.finished_at = datetime.utcnow()
        db.commit()
        return {
            "status": run.status,
            "items_checked": run.items_checked,
            "items_saved": run.items_saved,
            "official_recent": official_result,
        }
    except Exception as exc:
        db.rollback()
        run = db.get(OpsIntelRun, run.id)
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = datetime.utcnow()
        db.commit()
        return {"status": run.status, "error": run.error}
    finally:
        db.close()


async def periodic_collect_loop():
    while True:
        await collect_once()
        await asyncio.sleep(max(1, settings.ops_intel_interval_hours) * 3600)


def start_periodic_collector():
    global _task
    if settings.ops_intel_autostart and (_task is None or _task.done()):
        _task = asyncio.create_task(periodic_collect_loop())


def stop_periodic_collector():
    global _task
    if _task and not _task.done():
        _task.cancel()
    _task = None


def refine_official_items() -> dict:
    db = SessionLocal()
    counts = {"official_report_candidate": 0, "official_source": 0, "supplementary_source": 0, "needs_source_review": 0}
    try:
        rows = db.query(OpsIntelItem).all()
        for item in rows:
            quality = candidate_quality(
                {"url": item.source_url},
                item.source_url,
                item.title or "",
                item.summary or "",
                item.last_status or 0,
            )
            counts[quality] += 1
            tags = json.loads(item.tags or "[]")
            tags = [tag for tag in tags if tag not in counts]
            tags.append(quality)
            item.tags = json.dumps(list(dict.fromkeys(tags)))
            if quality == "official_report_candidate" and item.severity == "Low":
                item.severity = "Medium"
            item.updated_at = datetime.utcnow()
        db.commit()
        return {"items_refined": len(rows), **counts}
    finally:
        db.close()
