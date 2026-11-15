from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .calendar import parse_events
from .places import PLACES, resolve_place
from .graph import load_graph
from .routing import find_route, route_payload
from .ai import suggest_intent

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


@app.get("/effects.js")
def effects():
    return FileResponse(STATIC / "effects.js", media_type="text/javascript")


@app.get("/api/places")
def places():
    return [{"id": p.id, "name": p.name, "aliases": p.aliases,
             "map_grid": p.map_grid} for p in PLACES]


class RouteRequest(BaseModel):
    itinerary: list[str] = Field(min_length=2, max_length=14)
    mode: str = "walk"
    step_free: bool = True
    avoid_steep: bool = False


class InterpretRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    use_local_ai: bool = False


@app.post("/api/interpret")
def interpret(request: InterpretRequest):
    if not request.text.strip() or not request.use_local_ai:
        return {"status": "fallback", "suggestion": None}
    suggestion = suggest_intent(request.text)
    return {"status": "ai" if suggestion else "fallback", "suggestion": suggestion}


@app.post("/api/route")
def route(request: RouteRequest):
    if request.mode not in ("walk", "bus", "mixed") or any(
        not isinstance(name, str) or not name.strip() or len(name) > 200 for name in request.itinerary
    ):
        raise HTTPException(422, "Use 2–14 named places and a supported travel mode.")
    graph = load_graph()
    legs = []
    for origin, destination in zip(request.itinerary, request.itinerary[1:]):
        start = resolve_place(origin)
        end = resolve_place(destination)
        if request.mode != "walk":
            result = {"status": "external_transit_required", "message": "Plan this leg with current transit services."}
        elif not start or not end or start.id not in {p.id for p in graph.places} or end.id not in {p.id for p in graph.places}:
            result = {"status": "unavailable", "message": "One or both places are outside the reviewed path graph."}
        elif start.id == end.id:
            result = {"status": "same_place", "message": "Both endpoints are the same place."}
        else:
            found = find_route(graph, start.id, end.id,
                               step_free=request.step_free, avoid_steep=request.avoid_steep)
            result = route_payload(graph, found) if found else {
                "status": "unavailable", "message": "No verified route is available for these places and preferences."
            }
        legs.append({"from": origin, "to": destination, **result})
    return {"status": "verified" if all(leg["status"] in ("verified", "same_place") for leg in legs)
            else "unavailable", "legs": legs}


@app.post("/api/calendar/import")
async def import_calendar(request: Request):
    if request.headers.get("content-type", "").split(";")[0] not in ("text/calendar", "application/octet-stream"):
        raise HTTPException(415, "Upload an .ics calendar file.")
    data = await request.body()
    try:
        return parse_events(data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
