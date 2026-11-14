# Campus graph review

Milestone 2 starts a small, evidence-backed graph in [`app/data/campus_graph.json`](../app/data/campus_graph.json). It is research data. The itinerary UI does not consume it as routing data. Run `.venv/bin/python -m scripts.validate_graph` after any edit.

## Current subset

- Student Union and Integrative Learning Center appear in the [January 2026 campus map](https://www.umass.edu/sites/default/files/2026-03/FY26_Campus_Map_Update_with_INDEX-FINAL-EDITORIAL_FINAL.pdf).
- The [2024 accessibility map](https://www.umass.edu/planning-design-construction/sites/default/files/2024-11/CampusMap-Accessbility-Large-2024.pdf) depicts them as fully accessible and shows entrance symbols. The [official maps page](https://www.umass.edu/planning-design-construction/maps-and-tours) says its accessibility data is current as of August 2022 and cannot guarantee completeness or accuracy.
- Three entrance symbols are transcribed as map markers. Their exact doors and present-day status are unknown.
- One possible outdoor connection between the buildings is a **candidate** with unknown step-free status, grade, distance, and geometry. The maps do not prove this connection. There are zero production edges and zero edges eligible for step-free routing.

## Data contract

The file has a versioned schema with evidence, places, nodes, entrances, and edges. A place ID must match the searchable catalog. Every place, entrance, and edge cites evidence IDs. Evidence records source and review dates, URL, review method, and the narrow observation it supports. An edge records its endpoints, mode, review status, step-free and grade status, distance, geometry, and provenance. `unknown` means no claim has been established; it is never treated as step-free.

The validator checks references, IDs, numeric bounds, geometry, source links, and status consistency. A production edge needs field-reviewed access status (step-free or blocked), grade, distance, and geometry; any entrance at its endpoints must also have field-reviewed access. `strict_step_free_edges` rejects an invalid graph and returns only production edges marked step-free. A reviewed stair segment may be used for ordinary walking but is excluded by the step-free preference. The validator does not itself confirm that a field observation was accurate or remains current.

## Before promoting a candidate

1. Identify the precise entrances and trace the full outdoor segment on site. Record coordinates and distance, surface, steps/curbs, ramps, and grade, including the steepest relevant portion.
2. Record the reviewer, field-review date, method, and a durable evidence link. Check the current [campus impact notices](https://www.umass.edu/facilities/current-campus-impact-notices) for closures or detours and note when the status was checked.
3. Add evidence for each verified entrance and segment. Mark an edge `production` only when its access status and both applicable entrances have been field-reviewed. Record steps as `blocked` for step-free routing. Rerun the validator and tests.
4. Review freshness and current closures again before exposing any route in the app. The current graph has no expiry or live closure feed, so that work belongs to the routing milestone.
