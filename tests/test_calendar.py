from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.calendar import parse_events
from app.main import app

TZ = ZoneInfo("America/New_York")
FIXTURES = Path(__file__).parent / "fixtures"


def read(name):
    return (FIXTURES / name).read_bytes()


def test_one_off_and_next_class():
    result = parse_events(read("one_off.ics"), datetime(2026, 11, 17, 8, tzinfo=TZ))
    assert len(result["events"]) == 1
    assert result["next_event_id"] == result["events"][0]["id"]
    assert result["events"][0]["place_name"] == "Computer Science Building"


def test_recurrence_exdate_and_floating_time():
    result = parse_events(read("recurring.ics"), datetime(2026, 11, 8, 12, tzinfo=TZ))
    assert [e["start"][:10] for e in result["events"]] == ["2026-11-09", "2026-11-23", "2026-11-30"]
    assert result["events"][0]["start"].endswith("-05:00")


def test_missing_and_unmatched_location_are_not_next_class():
    result = parse_events(read("missing_location.ics"), datetime(2026, 11, 17, 7, tzinfo=TZ))
    assert result["next_event_id"] is None
    assert result["events"][0]["missing_location"] is True
    assert result["events"][1]["unresolved"] is True


def test_timezone_transition():
    result = parse_events(read("timezone.ics"), datetime(2026, 11, 1, 8, tzinfo=TZ))
    assert result["events"][0]["start"] == "2026-11-01T09:30:00-05:00"


def test_import_endpoint_reports_invalid_file():
    response = TestClient(app).post("/api/calendar/import", content=b"oops", headers={"content-type": "text/calendar"})
    assert response.status_code == 400


def test_supplied_export_shape_without_committing_personal_schedule():
    data = b"""BEGIN:VCALENDAR\r
VERSION:2.0\r
X-WR-TIMEZONE:America/New_York\r
BEGIN:VEVENT\r
DTSTART:20260908T100000\r
DURATION:PT50M\r
RRULE:FREQ=WEEKLY;BYDAY=TU,TH;UNTIL=20261215\r
SUMMARY:DEMO 101*\r
LOCATION:Morrill Sci. Ctr. (II) rm 131*\r
END:VEVENT\r
END:VCALENDAR\r
"""
    result = parse_events(data, datetime(2026, 11, 14, 12, tzinfo=TZ))
    assert result["events"][0]["start"] == "2026-11-17T10:00:00-05:00"
    assert result["events"][0]["place_id"] == "morrill-ii"


@pytest.mark.parametrize("payload", [b"", b"broken"])
def test_bad_input(payload):
    with pytest.raises(ValueError):
        parse_events(payload)
