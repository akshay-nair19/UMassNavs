"""Display-only place names. None of these entries imply a verified route."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    aliases: tuple[str, ...]


PLACES = (
    Place("du-bois", "W. E. B. Du Bois Library", ("du bois library", "dubois library", "library")),
    Place("morrill-ii", "Morrill Science Center II", ("morrill sci ctr ii", "morrill sci ctr (ii)", "morrill science center ii")),
    Place("goessmann", "Goessmann Laboratory", ("goessmann lab", "goessmann lab add", "goessmann laboratory addition")),
    Place("hasbrouck", "Hasbrouck Laboratory", ("hasbrouck lab add", "hasbrouck laboratory", "hasbrouck lab")),
    Place("engineering-lab", "Engineering Laboratory", ("engineering laboratory",)),
    Place("ilc", "Integrated Learning Center", ("integ learning center", "integrated learning center", "ilc")),
    Place("cs-building", "Computer Science Building", ("computer science building", "cs building")),
)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def resolve_place(value: str | None) -> Place | None:
    if not value:
        return None
    # SPIRE sample locations contain a room and a trailing asterisk. Match
    # only at the start so a room label cannot resolve to a different place.
    target = _normalized(value.strip().rstrip("*"))
    candidates = sorted(
        ((alias, place) for place in PLACES for alias in (place.name, *place.aliases)),
        key=lambda item: len(_normalized(item[0])),
        reverse=True,
    )
    for alias, place in candidates:
        key = _normalized(alias)
        if target == key or target.startswith(key + " "):
            return place
    return None
