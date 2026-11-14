from dataclasses import replace

from fastapi.testclient import TestClient

from app.graph import load_graph, validate_graph
from app.main import app
from app.routing import find_route, route_payload


def reviewed_fixture():
    """Synthetic field-reviewed graph; never shipped as campus path data."""
    graph = load_graph()
    field = replace(graph.evidence[0], id="synthetic-field", source_title="Synthetic field review",
                    source_url="https://example.org/synthetic-field", review_method="field")
    entrances = tuple(replace(entrance, current_step_free_status="verified",
                              evidence_ids=(field.id,)) for entrance in graph.entrances)
    prototype = graph.edges[0]

    def edge(identifier, start, end, distance, grade, status="verified", stage="production"):
        return replace(prototype, id=identifier, from_node=start, to_node=end, distance_m=distance,
                       grade_percent=grade, grade_status="verified", step_free_status=status,
                       status=stage, geometry=((42.39, -72.53), (42.391, -72.531)),
                       source_url=field.source_url, source_date=field.source_date,
                       review_method="field", evidence_ids=(field.id,))

    return replace(graph, evidence=(*graph.evidence, field), entrances=entrances, edges=(
        edge("stairs", "student-union-northwest-map-marker", "ilc-southwest-map-marker", 10, 2, "blocked"),
        edge("north-path", "student-union-northwest-map-marker", "ilc-southwest-map-marker", 50, 7),
        edge("south-path", "student-union-south-map-marker", "ilc-southwest-map-marker", 100, 2),
        edge("unknown-shortcut", "student-union-south-map-marker", "ilc-southwest-map-marker", 1, 2,
             "unknown", "candidate"),
    ))


def test_filters_stairs_unknown_and_steep_paths_with_alternate_entrance():
    graph = reviewed_fixture()
    assert validate_graph(graph) == []
    ordinary = find_route(graph, "student-union", "ilc", step_free=False)
    assert ordinary.edge_ids == ("stairs",)
    step_free = find_route(graph, "student-union", "ilc")
    assert step_free.edge_ids == ("north-path",)
    gentler = find_route(graph, "student-union", "ilc", avoid_steep=True)
    assert gentler.edge_ids == ("south-path",)


def test_disconnected_route_and_source_attribution():
    graph = reviewed_fixture()
    assert find_route(replace(graph, edges=()), "student-union", "ilc") is None
    route = find_route(graph, "student-union", "ilc")
    payload = route_payload(graph, route)
    assert payload["distance_m"] == 50
    assert payload["segments"][0]["evidence"][0]["url"] == "https://example.org/synthetic-field"
    assert payload["segments"][0]["from"].startswith("Northwest")
    assert payload["segments"][0]["to"].startswith("Southwest")


def test_real_campus_api_fails_closed_and_preserves_stops():
    response = TestClient(app).post("/api/route", json={"itinerary": [
        "Student Union", "Integrative Learning Center", "Student Union"]})
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert len(response.json()["legs"]) == 2
    assert all(leg["status"] == "unavailable" for leg in response.json()["legs"])
