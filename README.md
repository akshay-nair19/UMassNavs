# UMass Campus Navigator

Local-first prototype for planning a campus itinerary and importing an iCalendar class schedule. It previews an ordered itinerary and **does not calculate or certify routes**. No path, accessibility, grade, or bus-stop connection data has been verified.

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

- Enter or search for a starting point, up to 12 ordered stops, and a final destination; manually entered places remain usable as text. Move or remove stops before reviewing the itinerary.
- Search a catalog drawn from all 200 entries in the [UMass January 2026 campus map building index](https://www.umass.edu/sites/default/files/2026-03/FY26_Campus_Map_Update_with_INDEX-FINAL-EDITORIAL_FINAL.pdf), plus existing calendar aliases. The picker currently has 201 entries after near-duplicate names are merged. Map grid references are labels, not precise coordinates or route evidence.
- Select walking, public bus, or walking plus public bus. The bus modes show [UMass Transit routes and schedules](https://www.umass.edu/transportation/transit/pvta-routes-and-schedules) and the [PVTA trip planner](https://www.pvta.com/) for current service. After reviewing an itinerary, they also offer a separate [Google Maps transit directions](https://developers.google.com/maps/documentation/urls/get-started) link for each leg. You must click a link to leave the local app and share that leg's place names with Google. Check that the external service found the right places and current service; this app does not compute a bus stop, departure, transfer, or accessibility claim.
- Import an `.ics` file in a bounded 30-day window. Recurring meetings at the same matched building appear as one destination card with its next meeting and class names. The next upcoming event with a matched campus location is selected automatically.
- Handle `DTSTART`, `DTEND` or `DURATION`, `RRULE`, `EXDATE`, `RECURRENCE-ID`, timezone-aware dates, folded iCalendar lines, and escaped text through the parsing libraries. Duplicate expanded occurrences are removed within one import.
- Recognize a small set of building names and abbreviations from the supplied schedule. These aliases are **display helpers only**. A match does not verify an entrance or path.
- Interpret simple `from … to …` requests when a known place is named. A text destination that conflicts with the selected class prompts a choice. The destination field can always be edited.

## Assumptions and limits

- The supplied SPIRE-style export has floating local times, `X-WR-TIMEZONE:America/New_York`, recurring rules, `DURATION`, and no event `UID`. Floating times use `X-WR-TIMEZONE` when valid; otherwise they use campus time. This is an explicit assumption for that export, not a general SPIRE format guarantee.
- The app does not save calendars or schedules. The browser sends an uploaded file to the FastAPI server on `127.0.0.1`; the server parses it in memory and returns upcoming event fields. There is no account or cloud service. Do not expose the local server to a public interface.
- The file size limit is 2 MB. Events more than 30 days away do not appear. An unmatched or missing location is shown, but never automatically becomes the next-class destination.
- The official map is a broad index, not a live inventory or routable map. It includes areas, landmarks, and entries marked under construction or renovation. A place in the picker does not imply it is open, reachable, or accessible. Calendar aliases may still misidentify abbreviated rooms; correct them in the UI. The supplied `Arnold Room 140` now matches the indexed place **Arnold**, but the room itself remains unverified. The original personal calendar is intentionally excluded from the repository; synthetic fixtures cover its relevant shape.
- The text request parser only recognizes known names in a basic `from … to …` pattern and the phrase “my next class.” It does not call an AI model.
- Preferences are recorded in the interface only. No route, distance, travel time, accessibility status, or geographic map is shown because the reviewed graph has no eligible path. Opening the external transit links leaves the local app and may share information you enter on those services.
- The dark glass interface uses a local-only visual effects script. Its pointer cursor and card spotlight are disabled for coarse pointers or reduced-motion settings; the native cursor and all form controls remain available.

## Campus graph status

Milestone 2 now includes a typed graph schema, a small source-reviewed subset, a validator, and a strict gate for future step-free routing. The [graph review notes](docs/graph-review.md) explain the sources and the field checks needed to promote a candidate connection. Run `.venv/bin/python -m scripts.validate_graph` to check the data. It currently reports **zero eligible step-free edges**; no route is calculated or certified.
