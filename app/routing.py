"""Shortest path over reviewed graph edges; never infer a connection from a map."""

import heapq
from itertools import count

from .domain import Route
from .graph import CampusGraph, validate_graph


def find_route(graph: CampusGraph, start_place_id: str, end_place_id: str,
               *, step_free: bool = True, avoid_steep: bool = False) -> Route | None:
    errors = validate_graph(graph)
    if errors:
        raise ValueError("Invalid campus graph: " + "; ".join(errors))
    if start_place_id == end_place_id or not any(p.id == start_place_id for p in graph.places) or not any(
        p.id == end_place_id for p in graph.places
    ):
        return None

    entrances = {item.node_id: item for item in graph.entrances if item.current_step_free_status == "verified"}
    starts = {item.node_id for item in graph.entrances if item.place_id == start_place_id and item.node_id in entrances}
    ends = {item.node_id for item in graph.entrances if item.place_id == end_place_id and item.node_id in entrances}
    if not starts or not ends:
        return None

    adjacency: dict[str, list] = {}
    for edge in graph.edges:
        if edge.status != "production" or edge.step_free_status == "unknown":
            continue
        if step_free and edge.step_free_status != "verified":
            continue
        if avoid_steep and (edge.grade_percent is None or abs(edge.grade_percent) > 5):
            continue
        adjacency.setdefault(edge.from_node, []).append((edge.to_node, edge))
        adjacency.setdefault(edge.to_node, []).append((edge.from_node, edge))

    serial = count()
    queue = [(0.0, next(serial), node, (node,), ()) for node in sorted(starts)]
    heapq.heapify(queue)
    best: dict[str, float] = {}
    while queue:
        distance, _, node, node_path, path = heapq.heappop(queue)
        if distance >= best.get(node, float("inf")):
            continue
        best[node] = distance
        if node in ends:
            edge_ids = tuple(edge.id for edge in path)
            evidence_ids = tuple(dict.fromkeys(ref for edge in path for ref in edge.evidence_ids))
            return Route(start_place_id, end_place_id, node_path, edge_ids, evidence_ids, "verified")
        for neighbor, edge in adjacency.get(node, []):
            if distance + edge.distance_m < best.get(neighbor, float("inf")):
                heapq.heappush(queue, (distance + edge.distance_m, next(serial), neighbor,
                                       (*node_path, neighbor), (*path, edge)))
    return None


def route_payload(graph: CampusGraph, route: Route) -> dict:
    """Expose reviewed facts only; labels are schematic, not turn-by-turn geometry."""
    nodes = {item.id: item for item in graph.nodes}
    edges = {item.id: item for item in graph.edges}
    evidence = {item.id: item for item in graph.evidence}
    segments = []
    for index, edge_id in enumerate(route.edge_ids):
        edge = edges[edge_id]
        segments.append({
            "id": edge.id,
            "from": nodes[route.node_ids[index]].relative_location,
            "to": nodes[route.node_ids[index + 1]].relative_location,
            "mode": edge.mode,
            "distance_m": edge.distance_m,
            "grade_percent": edge.grade_percent,
            "step_free_status": edge.step_free_status,
            "evidence": [{"title": evidence[ref].source_title, "url": evidence[ref].source_url,
                          "source_date": evidence[ref].source_date, "review_date": evidence[ref].review_date}
                         for ref in edge.evidence_ids],
        })
    return {"status": route.status, "distance_m": sum(segment["distance_m"] for segment in segments),
            "segments": segments}
