from app.places import CATALOG, PLACES, resolve_place


def test_campus_map_catalog_has_unique_picker_entries():
    assert len(CATALOG["locations"]) == 200
    assert len({place.id for place in PLACES}) == len(PLACES)
    assert resolve_place("Wysocki House").map_grid == "C1"
    assert resolve_place("Integ. Learning Center S120").id == "ilc"
    assert resolve_place("Arnold Room 140").name == "Arnold"
