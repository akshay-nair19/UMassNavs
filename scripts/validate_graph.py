"""Run with: .venv/bin/python -m scripts.validate_graph"""

import argparse
from pathlib import Path

from app.graph import DEFAULT_GRAPH, load_graph, strict_step_free_edges, validate_graph


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate campus path evidence")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_GRAPH)
    args = parser.parse_args()
    try:
        graph = load_graph(args.path)
        errors = validate_graph(graph)
    except (OSError, ValueError) as exc:
        print(f"Invalid graph: {exc}")
        return 1
    if errors:
        for error in errors:
            print(f"Invalid graph: {error}")
        return 1
    print(f"Valid graph: {len(graph.places)} places, {len(graph.entrances)} entrances, "
          f"{len(graph.edges)} recorded edge(s), "
          f"{len(strict_step_free_edges(graph))} eligible step-free edges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
