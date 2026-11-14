"""Load and validate reviewed campus graph data."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import json
import math

from .domain import Entrance, Evidence, PathEdge, PathNode, Place
from .places import PLACES

DEFAULT_GRAPH = Path(__file__).parent / "data" / "campus_graph.json"


@dataclass(frozen=True)
class CampusGraph:
    evidence: tuple[Evidence, ...]
    places: tuple[Place, ...]
    nodes: tuple[PathNode, ...]
    entrances: tuple[Entrance, ...]
    edges: tuple[PathEdge, ...]


def load_graph(path: Path = DEFAULT_GRAPH) -> CampusGraph:
    raw = json.loads(path.read_text())
    if raw.get("schema_version") != 1:
        raise ValueError("Unsupported campus graph schema version")
    try:
        return CampusGraph(
            evidence=tuple(Evidence(**item) for item in raw["evidence"]),
            places=tuple(Place(**{**item, "evidence_ids": tuple(item["evidence_ids"])}) for item in raw["places"]),
            nodes=tuple(PathNode(**item) for item in raw["nodes"]),
            entrances=tuple(Entrance(**{**item, "evidence_ids": tuple(item["evidence_ids"])}) for item in raw["entrances"]),
            edges=tuple(PathEdge(**{**item,
                "evidence_ids": tuple(item["evidence_ids"]),
                "geometry": tuple(tuple(point) for point in item["geometry"]) if item["geometry"] is not None else None,
            }) for item in raw["edges"]),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed campus graph: {exc}") from exc


def _date(value: str) -> bool:
    try:
        date.fromisoformat(value + "-01" if len(value) == 7 else value)
        return True
    except (TypeError, ValueError):
        return False


def _ids_are_unique(items: tuple, label: str, errors: list[str]) -> None:
    ids = [item.id for item in items]
    if any(not identifier for identifier in ids) or len(set(ids)) != len(ids):
        errors.append(f"{label} IDs must be nonempty and unique")


def validate_graph(graph: CampusGraph) -> list[str]:
    errors: list[str] = []
    for label, items in (("Evidence", graph.evidence), ("Place", graph.places),
                         ("Node", graph.nodes), ("Entrance", graph.entrances), ("Edge", graph.edges)):
        _ids_are_unique(items, label, errors)
    evidence = {item.id: item for item in graph.evidence}
    places = {item.id: item for item in graph.places}
    nodes = {item.id: item for item in graph.nodes}
    entrances_by_node = {item.node_id: item for item in graph.entrances}
    catalog_ids = {item.id for item in PLACES}

    def check_evidence(owner: str, ids: tuple[str, ...]) -> None:
        if not ids or any(identifier not in evidence for identifier in ids):
            errors.append(f"{owner} needs existing evidence IDs")

    for item in graph.evidence:
        if not item.source_url.startswith("https://") or not item.source_title or not item.observation:
            errors.append(f"Evidence {item.id} needs a source URL, title, and observation")
        if not _date(item.source_date) or not _date(item.review_date):
            errors.append(f"Evidence {item.id} has invalid source/review dates")
        if item.review_method not in ("desk_visual", "field"):
            errors.append(f"Evidence {item.id} has invalid review method")

    for item in graph.places:
        if item.id not in catalog_ids:
            errors.append(f"Place {item.id} is missing from the searchable catalog")
        if item.reported_building_access not in ("fully_accessible", "all_floors_not_all_doors", "partial", "not_accessible", "unknown"):
            errors.append(f"Place {item.id} has invalid reported access")
        check_evidence(f"Place {item.id}", item.evidence_ids)

    for item in graph.nodes:
        if item.kind not in ("entrance", "waypoint") or (item.place_id and item.place_id not in places):
            errors.append(f"Node {item.id} has invalid kind or place")
        if not item.relative_location:
            errors.append(f"Node {item.id} needs a relative location")
        if (item.latitude is None) != (item.longitude is None):
            errors.append(f"Node {item.id} needs both coordinates or neither")
        if item.latitude is not None and not (
            isinstance(item.latitude, (int, float)) and isinstance(item.longitude, (int, float))
            and -90 <= item.latitude <= 90 and -180 <= item.longitude <= 180
        ):
            errors.append(f"Node {item.id} has invalid coordinates")

    for item in graph.entrances:
        node = nodes.get(item.node_id)
        if item.place_id not in places or node is None or node.kind != "entrance" or node.place_id != item.place_id:
            errors.append(f"Entrance {item.id} needs a matching entrance node and place")
        if item.current_step_free_status not in ("verified", "blocked", "unknown"):
            errors.append(f"Entrance {item.id} has invalid current access status")
        check_evidence(f"Entrance {item.id}", item.evidence_ids)
        if item.current_step_free_status == "verified" and not any(
            evidence.get(ref) and evidence[ref].review_method == "field" for ref in item.evidence_ids
        ):
            errors.append(f"Entrance {item.id} cannot be verified by desk review alone")

    for item in graph.edges:
        if item.from_node not in nodes or item.to_node not in nodes or item.from_node == item.to_node:
            errors.append(f"Edge {item.id} needs two distinct existing nodes")
        if item.mode not in ("pedestrian", "elevator") or item.status not in ("candidate", "production"):
            errors.append(f"Edge {item.id} has invalid mode or status")
        if item.step_free_status not in ("verified", "blocked", "unknown"):
            errors.append(f"Edge {item.id} has invalid step-free status")
        if item.grade_status not in ("verified", "unknown") or (item.grade_percent is None) != (item.grade_status == "unknown"):
            errors.append(f"Edge {item.id} has inconsistent grade evidence")
        if item.grade_percent is not None and not (
            isinstance(item.grade_percent, (int, float)) and math.isfinite(item.grade_percent)
        ):
            errors.append(f"Edge {item.id} has invalid grade")
        if item.distance_m is not None and not (
            isinstance(item.distance_m, (int, float)) and math.isfinite(item.distance_m) and item.distance_m > 0
        ):
            errors.append(f"Edge {item.id} has invalid distance")
        if item.geometry is not None:
            if len(item.geometry) < 2 or any(
                len(point) != 2 or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in point)
                or not (-90 <= point[0] <= 90 and -180 <= point[1] <= 180)
                for point in item.geometry
            ):
                errors.append(f"Edge {item.id} has invalid geometry")
        if not item.source_url.startswith("https://") or not _date(item.source_date) or not _date(item.review_date):
            errors.append(f"Edge {item.id} needs source URL and valid source/review dates")
        if not item.note:
            errors.append(f"Edge {item.id} needs a review note")
        check_evidence(f"Edge {item.id}", item.evidence_ids)
        if not any(evidence.get(ref) and evidence[ref].source_url == item.source_url for ref in item.evidence_ids):
            errors.append(f"Edge {item.id} source URL must match cited evidence")
        if item.status == "production" and (
            item.step_free_status == "unknown" or item.grade_status != "verified"
            or item.distance_m is None or item.geometry is None
            or item.review_method != "field"
            or not any(evidence.get(ref) and evidence[ref].review_method == "field" for ref in item.evidence_ids)
        ):
            errors.append(f"Edge {item.id} cannot be production without field-reviewed access, grade, distance, and geometry")
        if item.status == "production" and any(
            nodes.get(node_id) and nodes[node_id].kind == "entrance"
            and (node_id not in entrances_by_node or entrances_by_node[node_id].current_step_free_status != "verified")
            for node_id in (item.from_node, item.to_node)
        ):
            errors.append(f"Edge {item.id} cannot be production with an unverified entrance")
    return errors


def strict_step_free_edges(graph: CampusGraph) -> tuple[PathEdge, ...]:
    """Routing gate for Milestone 3; candidate and unknown edges never qualify."""
    errors = validate_graph(graph)
    if errors:
        raise ValueError("Invalid campus graph: " + "; ".join(errors))
    return tuple(edge for edge in graph.edges if edge.status == "production" and edge.step_free_status == "verified")
