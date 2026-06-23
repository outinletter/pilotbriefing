import json
import re
from datetime import datetime, timedelta
from html import unescape
from urllib.parse import parse_qs, urljoin, urlparse

import httpx

from ..database import SessionLocal
from ..models import OpsIntelItem

NTSB_MONTHLY_URL = "https://www.ntsb.gov/Pages/monthly.aspx"
FAA_TRANSPORT_LIBRARY_URL = "https://www.faa.gov/lessonslearned/transportairplane/accidents/transport-airplane-lessons-learned-library"
ASRS_REPORTSETS_URL = "https://asrs.arc.nasa.gov/search/reportsets.html"

ASRS_RELEVANT_KEYWORDS = [
    "far 121", "air carrier", "commuter", "corporate", "fatigue", "smoke", "fire",
    "fumes", "crm", "fuel", "gps", "weather", "maintenance", "turbojet", "rnav",
    "runway", "wake turbulence", "flight attendant",
]

MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def cutoff_date(years_back: int) -> datetime:
    return datetime.utcnow() - timedelta(days=years_back * 365)


def parse_date(text: str) -> datetime | None:
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def category_for_title(title: str) -> str:
    text = title.lower()
    if any(word in text for word in ["fatigue", "crm", "flight crew", "flight attendant"]):
        return "Human Factors / CRM"
    if any(word in text for word in ["gps", "runway", "weather", "fuel", "rnav", "wake"]):
        return "Flight Operations"
    if any(word in text for word in ["maintenance", "fumes", "smoke", "fire", "turbojet"]):
        return "Accident / Incident"
    return "Accident / Incident"


def official_summary(source_name: str, title: str, note: str) -> str:
    return f"{title}. Official source: {source_name}. {note}"


def upsert_official_item(
    db,
    *,
    source_name: str,
    source_url: str,
    title: str,
    category: str,
    severity: str,
    summary: str,
    tags: list[str],
) -> bool:
    item = db.query(OpsIntelItem).filter(OpsIntelItem.source_url == source_url).first()
    created = False
    if not item:
        item = OpsIntelItem(source_name=source_name, source_url=source_url)
        db.add(item)
        created = True
    item.title = title
    item.category = category
    item.severity = severity
    item.summary = summary
    item.operation_type = "Part 121 / Part 135"
    item.operational_lesson = "Screen this official item for Part 121/135 operational precursors, crew decision points, dispatch implications, and training value."
    item.a350_b787_applicability = "Review for long-haul widebody relevance, including ETOPS, fatigue, weather, navigation, maintenance control, and arrival/approach threat management."
    item.recommended_action = "Verify report details from the official source, classify Part 121/135 applicability, then extract briefing-ready lessons without inferring cause beyond the source."
    item.tags = json.dumps(list(dict.fromkeys(tags)))
    item.last_status = 200
    item.last_checked_at = datetime.utcnow()
    item.updated_at = datetime.utcnow()
    return created


async def parse_ntsb_monthly(client: httpx.AsyncClient, db, years_back: int) -> dict:
    response = await client.get(NTSB_MONTHLY_URL)
    response.raise_for_status()
    cutoff = cutoff_date(years_back)
    created = 0
    checked = 0
    seen = set()
    for match in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>', response.text, re.IGNORECASE):
        href = unescape(match.group(1))
        parsed = urlparse(href)
        query = parse_qs(parsed.query)
        try:
            year = int(query.get("year", [""])[0])
            month = int(query.get("month", [""])[0])
        except ValueError:
            continue
        if not (1 <= month <= 12):
            continue
        event_month = datetime(year, month, 1)
        if event_month < datetime(cutoff.year, cutoff.month, 1):
            continue
        url = urljoin(NTSB_MONTHLY_URL, href)
        if url in seen:
            continue
        seen.add(url)
        checked += 1
        title = f"NTSB Aviation Accident Synopses - {year} {MONTH_NAMES[month]}"
        if upsert_official_item(
            db,
            source_name="NTSB Monthly Aviation Accident Synopses",
            source_url=url,
            title=title,
            category="Accident / Incident",
            severity="Medium",
            summary=official_summary(
                "NTSB",
                title,
                "Monthly aviation accident synopses are saved as official recent-7-year candidates and still require Part 121/135 applicability screening.",
            ),
            tags=["NTSB", "recent_7_years", "ntsb_monthly_synopsis", "official_report_candidate", "part_121_135_screening_required"],
        ):
            created += 1
    return {"checked": checked, "created": created}


async def parse_faa_transport_library(client: httpx.AsyncClient, db, years_back: int) -> dict:
    response = await client.get(FAA_TRANSPORT_LIBRARY_URL)
    response.raise_for_status()
    cutoff = cutoff_date(years_back)
    created = 0
    rows = []
    for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", response.text):
        cells = re.findall(r"(?is)<td[^>]*>(.*?)</td>", row)
        if len(cells) < 2:
            continue
        date_text = clean_text(cells[0])
        event_date = parse_date(date_text)
        if not event_date:
            continue
        link_match = re.search(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', cells[1], re.IGNORECASE | re.DOTALL)
        if not link_match:
            continue
        url = urljoin(FAA_TRANSPORT_LIBRARY_URL, unescape(link_match.group(1)))
        operator = clean_text(link_match.group(2))
        flight = clean_text(cells[2]) if len(cells) > 2 else ""
        location = clean_text(cells[3]) if len(cells) > 3 else ""
        rows.append({
            "event_date": event_date,
            "date_text": date_text,
            "url": url,
            "operator": operator,
            "flight": flight,
            "location": location,
        })
    rows.sort(key=lambda item: item["event_date"], reverse=True)
    selected = [row for row in rows if row["event_date"] >= cutoff]
    if len(selected) < 10:
        seen = {row["url"] for row in selected}
        selected.extend(row for row in rows if row["url"] not in seen)
        selected = selected[:10]
    checked = 0
    extended_count = 0
    for row in selected:
        is_recent = row["event_date"] >= cutoff
        if not is_recent:
            extended_count += 1
        date_text = row["date_text"]
        operator = row["operator"]
        flight = row["flight"]
        location = row["location"]
        url = row["url"]
        title = f"FAA Transport Lessons Learned - {operator} {flight}".strip()
        checked += 1
        tags = ["FAA", "transport_airplane", "official_report_candidate", "part_121_135_relevant"]
        tags.append("recent_7_years" if is_recent else "extended_period_minimum_10")
        if upsert_official_item(
            db,
            source_name="FAA Transport Airplane Lessons Learned",
            source_url=url,
            title=title,
            category="Accident / Incident",
            severity="Medium",
            summary=official_summary(
                "FAA",
                title,
                f"Event date {date_text}. Location: {location or 'not listed'}. "
                f"{'Selected within recent 7-year window.' if is_recent else 'Selected by expanded period rule to keep at least 10 FAA cases in the database.'}",
            ),
            tags=tags,
        ):
            created += 1
    return {"checked": checked, "created": created, "extended_period": extended_count}


async def parse_asrs_report_sets(client: httpx.AsyncClient, db) -> dict:
    response = await client.get(ASRS_REPORTSETS_URL)
    response.raise_for_status()
    created = 0
    checked = 0
    pdf_links = list(re.finditer(r'<a[^>]+href=["\']([^"\']+\.pdf)["\']', response.text, re.IGNORECASE))
    for index, href_match in enumerate(pdf_links):
        next_start = pdf_links[index + 1].start() if index + 1 < len(pdf_links) else len(response.text)
        block = response.text[href_match.end():next_start]
        desc_match = re.search(r'(?is)<div class="fileDescription">\s*(.*?)\s*<div class="instructions">(.*?)</div>', block)
        if not desc_match:
            continue
        title = clean_text(desc_match.group(1))
        instructions = clean_text(desc_match.group(2))
        haystack = f"{title} {instructions}".lower()
        if not any(keyword in haystack for keyword in ASRS_RELEVANT_KEYWORDS):
            continue
        checked += 1
        url = urljoin(ASRS_REPORTSETS_URL, unescape(href_match.group(1)))
        if upsert_official_item(
            db,
            source_name="NASA ASRS Report Sets",
            source_url=url,
            title=f"ASRS Report Set - {title}",
            category=category_for_title(title),
            severity="Medium",
            summary=official_summary(
                "NASA ASRS",
                title,
                f"{instructions} ASRS report sets are pre-screened topic samples; individual report dates require downstream parsing.",
            ),
            tags=["ASRS", "asrs_report_set", "official_source", "part_121_135_relevant", "needs_individual_report_date_parse"],
        ):
            created += 1
    return {"checked": checked, "created": created}


async def collect_recent_official_events(years_back: int = 7) -> dict:
    db = SessionLocal()
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": "OpsBriefing/0.1"}) as client:
            ntsb = await parse_ntsb_monthly(client, db, years_back)
            faa = await parse_faa_transport_library(client, db, years_back)
            asrs = await parse_asrs_report_sets(client, db)
        db.commit()
        total_checked = ntsb["checked"] + faa["checked"] + asrs["checked"]
        total_created = ntsb["created"] + faa["created"] + asrs["created"]
        return {
            "status": "complete",
            "years_back": years_back,
            "sources": {"ntsb": ntsb, "faa": faa, "asrs": asrs},
            "items_checked": total_checked,
            "items_saved": total_created,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
