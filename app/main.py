from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from .calendar import parse_events
from .places import PLACES

app = FastAPI(title="UMass Campus Navigator", docs_url=None, redoc_url=None)
STATIC = Path(__file__).parent / "static"


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/app.css")
def css():
    return FileResponse(STATIC / "app.css", media_type="text/css")


@app.get("/app.js")
def js():
    return FileResponse(STATIC / "app.js", media_type="text/javascript")


@app.get("/api/places")
def places():
    return [{"id": p.id, "name": p.name, "aliases": p.aliases} for p in PLACES]


@app.post("/api/calendar/import")
async def import_calendar(request: Request):
    if request.headers.get("content-type", "").split(";")[0] not in ("text/calendar", "application/octet-stream"):
        raise HTTPException(415, "Upload an .ics calendar file.")
    data = await request.body()
    try:
        return parse_events(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
