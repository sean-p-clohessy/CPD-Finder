from __future__ import annotations

from datetime import datetime
import re
from dateutil import parser


DATE_LABEL = re.compile(r"(?:date\s*:\s*)?((?:mon|tues|wednes|thurs|fri|satur|sun)day\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(20\d{2})", re.I)
TIME_RANGE = re.compile(r"(?:time\s*:\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*[-–]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)", re.I)


def parse_date(value: str | None) -> str | None:
    if not value:
        return None
    iso_match = re.match(r"^(20\d{2})-(\d{2})-(\d{2})", value.strip())
    if iso_match:
        try:
            return datetime.strptime(iso_match.group(0), "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None
    match = DATE_LABEL.search(value)
    candidate = " ".join(match.groups()[1:]) if match else value
    try:
        return parser.parse(candidate, dayfirst=True, fuzzy=True).date().isoformat()
    except (ValueError, OverflowError):
        return None


def parse_times(value: str | None) -> tuple[str | None, str | None]:
    match = TIME_RANGE.search(value or "")
    if not match:
        return None, None
    def fmt(raw: str) -> str:
        return parser.parse(raw.strip()).strftime("%H:%M")
    try:
        return fmt(match.group(1)), fmt(match.group(2))
    except ValueError:
        return None, None


def infer_type(title: str, text: str = "") -> str:
    haystack = f"{title} {text}".casefold()
    for needle, label in (("webinar", "Webinar"), ("workshop", "Workshop"), ("conference", "Conference"), ("network", "Networking"), ("course", "Course"), ("programme", "Programme"), ("standardisation", "Standardisation")):
        if needle in haystack:
            return label
    return "Professional development"


def infer_delivery(text: str) -> tuple[str, str]:
    lowered = text.casefold()
    if any(word in lowered for word in ("online", "webinar", "virtual", "teams", "zoom")):
        return "Online", ""
    location = re.search(r"location\s*:\s*([^\n|]+)", text, re.I)
    return ("In person", location.group(1).strip()) if location else ("Unknown", "")
