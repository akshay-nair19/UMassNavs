# UMass Campus Navigator

Local-first prototype for entering a campus destination and importing an iCalendar class schedule. This first milestone previews a trip and **does not calculate or certify routes**. No map, accessibility, or grade data has been verified.

## Run locally

Requires Python 3.11 or newer.

```sh
cd /Users/akshaynair/umassClassFinder
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Use `Ctrl+C` to stop it. Run tests with `.venv/bin/python -m pip install pytest httpx` and `.venv/bin/python -m pytest -q`.

## What works

- Enter or search for a starting point and destination; manually entered places remain usable as text.
- Import an `.ics` file, inspect events in a bounded 30-day window, and select or correct a class destination. The next upcoming event with a matched campus location is selected automatically.
- Handle `DTSTART`, `DTEND` or `DURATION`, `RRULE`, `EXDATE`, `RECURRENCE-ID`, timezone-aware dates, folded iCalendar lines, and escaped text through the parsing libraries. Duplicate expanded occurrences are removed within one import.
- Recognize a small set of building names and abbreviations from the supplied schedule. These aliases are **display helpers only**. A match does not verify an entrance or path.
- Interpret simple `from … to …` requests when a known place is named. A text destination that conflicts with the selected class prompts a choice. The destination field can always be edited.

## Assumptions and limits

- The supplied SPIRE-style export has floating local times, `X-WR-TIMEZONE:America/New_York`, recurring rules, `DURATION`, and no event `UID`. Floating times use `X-WR-TIMEZONE` when valid; otherwise they use campus time. This is an explicit assumption for that export, not a general SPIRE format guarantee.
- The app does not save calendars or schedules. The browser sends an uploaded file to the FastAPI server on `127.0.0.1`; the server parses it in memory and returns upcoming event fields. There is no account or cloud service. Do not expose the local server to a public interface.
- The file size limit is 2 MB. Events more than 30 days away do not appear. An unmatched or missing location is shown, but never automatically becomes the next-class destination.
- The place alias list is small and may miss or misidentify a building, especially abbreviated locations. `Arnold Room 140` in the supplied export is deliberately left unmatched because its building identity has not been confirmed. Correct the destination in the UI. The original personal calendar is intentionally excluded from the repository; synthetic fixtures cover its relevant shape.
- The text request parser only recognizes known names in a basic `from … to …` pattern and the phrase “my next class.” It does not call an AI model.
- Preferences are recorded in the interface only. No route, distance, travel time, accessibility status, or map is shown because the required evidence-backed graph does not exist yet.

## Next step: evidence-backed campus data

Milestone 2 needs reviewed source documents and a small, manually checked set of connected campus paths and accessible building entrances. Each segment needs a source, source date, review date, and explicit step-free/grade evidence. Until then, the app will continue to say no verified route is available.
