"""Typed contracts for evidence-backed campus data and later route results."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

StepFree = Literal["verified", "blocked", "unknown"]
ReviewMethod = Literal["desk_visual", "field"]


@dataclass(frozen=True)
class Evidence:
    id: str
    kind: str
    source_title: str
    source_url: str
    source_date: str
    review_date: str
    review_method: ReviewMethod
    observation: str


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    reported_building_access: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class PathNode:
    id: str
    kind: Literal["entrance", "waypoint"]
    place_id: str | None
    relative_location: str
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class Entrance:
    id: str
    place_id: str
    node_id: str
    reported_door_symbol: str
    current_step_free_status: StepFree
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class PathEdge:
    id: str
    from_node: str
    to_node: str
    mode: Literal["pedestrian", "elevator"]
    status: Literal["candidate", "production"]
    step_free_status: StepFree
    grade_status: Literal["verified", "unknown"]
    grade_percent: float | None
    distance_m: float | None
    geometry: tuple[tuple[float, float], ...] | None
    source_url: str
    source_date: str
    review_date: str
    review_method: ReviewMethod
    evidence_ids: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class Event:
    id: str
    summary: str
    start: datetime
    end: datetime
    location: str
    place_id: str | None


@dataclass(frozen=True)
class Route:
    start_place_id: str
    end_place_id: str
    edge_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    status: Literal["verified", "unavailable"]
