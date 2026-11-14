"""Bounded, in-memory iCalendar import for the local UI."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
import hashlib

from icalendar import Calendar
import recurring_ical_events

from .places import resolve_place

CAMPUS_TZ = ZoneInfo("America/New_York")
MAX_BYTES = 2_000_000


def _aware(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=CAMPUS_TZ) if value.tzinfo is None else value.astimezone(CAMPUS_TZ)
    return datetime.combine(value, time.min, CAMPUS_TZ)


def parse_events(data: bytes, now: datetime | None = None, days: int = 30) -> dict:
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Choose a nonempty .ics file under 2 MB.")
    if days < 1 or days > 90:
        raise ValueError("Calendar window must be between 1 and 90 days.")
    now = _aware(now or datetime.now(CAMPUS_TZ))
    try:
        calendar = Calendar.from_ical(data)
        if calendar.name != "VCALENDAR":
            raise ValueError("This is not an iCalendar file.")
        # Floating times in the supplied export have no TZID. Their calendar
        # declares X-WR-TIMEZONE, which is a nonstandard display hint.
        floating_zone = str(calendar.get("X-WR-TIMEZONE", "America/New_York"))
        try:
            source_tz = ZoneInfo(floating_zone)
        except (KeyError, ValueError):
            source_tz = CAMPUS_TZ
        start = now.astimezone(source_tz)
        end = (now + timedelta(days=days)).astimezone(source_tz)
        occurrences = recurring_ical_events.of(calendar).between(start, end)
    except Exception as exc:
        raise ValueError(f"Could not read this calendar: {exc}") from exc

    events = []
    seen = set()
    duplicates_removed = 0
    for component in occurrences:
        if component.name != "VEVENT" or str(component.get("STATUS", "")).upper() == "CANCELLED":
            continue
        raw_start = component.decoded("DTSTART", None)
        if raw_start is None:
            continue
        if isinstance(raw_start, datetime) and raw_start.tzinfo is None:
            raw_start = raw_start.replace(tzinfo=source_tz)
        event_start = _aware(raw_start)
        if event_start < now or event_start >= now + timedelta(days=days):
            continue
        raw_end = component.decoded("DTEND", None)
        if raw_end is None:
            duration = component.decoded("DURATION", None)
            raw_end = raw_start + duration if duration else raw_start
        if isinstance(raw_end, datetime) and raw_end.tzinfo is None:
            raw_end = raw_end.replace(tzinfo=source_tz)
        event_end = _aware(raw_end)
        summary = str(component.get("SUMMARY", "Untitled event")).strip().rstrip("*").strip()
        location = str(component.get("LOCATION", "")).strip().rstrip("*").strip()
        place = resolve_place(location)
        uid = str(component.get("UID", "")).strip()
        # Missing UIDs occur in the provided export. The fingerprint identifies
        # an occurrence within this import; no identifier is persisted.
        fingerprint = f"{uid}|{event_start.isoformat()}|{summary}|{location}"
        event_id = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
        if event_id in seen:
            duplicates_removed += 1
            continue
        seen.add(event_id)
        events.append({
            "id": event_id, "summary": summary, "start": event_start.isoformat(),
            "end": event_end.isoformat(), "location": location,
            "place_id": place.id if place else None,
            "place_name": place.name if place else None,
            "unresolved": bool(location) and place is None,
            "missing_location": not bool(location),
        })
    events.sort(key=lambda event: (event["start"], event["summary"]))
    next_event = next((event for event in events if event["place_id"]), None)
    return {"events": events, "next_event_id": next_event["id"] if next_event else None,
            "timezone": "America/New_York", "window_days": days,
            "duplicates_removed": duplicates_removed}
